"""
SQL-level column lineage extraction using SQLGlot.

Parses compiled SQL from dbt models and extracts which source columns
flow into which target columns, tracking through aliases, functions,
CASE/WHEN, JOINs, CTEs, and window functions.
"""

from __future__ import annotations

from sqlglot import exp, parse_one

from lineage.models import ColumnLineage, LineageGraph, TableNode

# Cache for parsed SQLGlot expressions
_PARSE_CACHE: dict[str, exp.Expression] = {}


def _parse_cached(sql: str, read_dialect: str = "spark") -> exp.Expression:
    """Parse SQL with a string cache for performance."""
    cache_key = sql.strip()
    if cache_key not in _PARSE_CACHE:
        try:
            _PARSE_CACHE[cache_key] = parse_one(sql, read=read_dialect)
        except Exception:
            try:
                _PARSE_CACHE[cache_key] = parse_one(sql, read="postgres")
            except Exception:
                _PARSE_CACHE[cache_key] = parse_one(sql, read="ansi")
    return _PARSE_CACHE[cache_key]


def clear_cache() -> None:
    """Clear the SQL parse cache."""
    _PARSE_CACHE.clear()


def _table_name_to_unique_id(table_name: str, source_tables: dict[str, TableNode]) -> str | None:
    """
    Try to match a SQL table name (possibly schema-qualified) to a source unique_id.
    Handles forms like: raw_orders, "raw_orders", "ecommerce"."raw_orders".
    """
    # Strip quotes
    clean = table_name.strip('"[]`')
    # Try direct match
    if clean in source_tables:
        return clean
    # Try unique_id match (e.g. "source.ecommerce.raw_orders")
    if table_name in source_tables:
        return table_name
    # Try partial match (last segment)
    segments = clean.split(".")
    for seg in segments:
        if seg in source_tables:
            return seg
    return None


class ColumnExtractor:
    """
    Walks a sqlglot AST to extract column-level lineage.

    Tracks SELECT expressions, aliases, source table.column references,
    CTE alias references, JOINs, and subqueries.
    """

    def __init__(self, compiled_sql: str, source_tables: dict[str, TableNode]):
        self.sql = compiled_sql
        # unique_id -> TableNode
        self.source_tables = source_tables
        # name -> unique_id (for both table names and aliases)
        self._name_to_uid: dict[str, str] = {}
        self.cte_map: dict[str, exp.Expression] = {}
        self.lineage: list[ColumnLineage] = []
        self.parsed: exp.Expression | None = None

        # Build a name->uid mapping for quick lookup
        for uid, node in source_tables.items():
            # Map by table name (short)
            short_name = node.name
            if short_name not in self._name_to_uid:
                self._name_to_uid[short_name] = uid
            # Map by unique_id segments
            parts = uid.split(".")
            for p in parts:
                if p and p not in self._name_to_uid:
                    self._name_to_uid[p] = uid

    def extract(self) -> list[ColumnLineage]:
        """Main entry point — parse SQL and extract all column lineage."""
        if not self.sql.strip():
            return []

        try:
            self.parsed = _parse_cached(self.sql)
        except Exception:
            return []

        self._collect_ctes(self.parsed)
        self._walk(self.parsed)
        return self.lineage

    def _collect_ctes(self, node: exp.Expression) -> None:
        """Collect all CTEs from the query."""
        for cte in node.find_all(exp.CTE):
            alias = cte.alias
            if alias:
                self.cte_map[alias] = cte
                self._name_to_uid[alias] = alias  # CTE acts as its own source

    def _walk(self, node: exp.Expression) -> None:
        """Recursively walk the AST."""
        if isinstance(node, exp.Select):
            self._walk_select(node)
        elif isinstance(node, (exp.Union, exp.Except, exp.Intersect)):
            if node.this:
                self._walk(node.this)

    def _walk_select(self, select: exp.Select) -> None:
        """Process a SELECT statement."""
        # Build source_refs from FROM and JOINs
        from_refs = self._resolve_from(select)
        join_refs = self._resolve_joins(select)
        all_refs = {**from_refs, **join_refs}

        for expr in select.expressions:
            self._resolve_expression(expr, all_refs)

    def _resolve_from(self, select: exp.Select) -> dict[str, tuple[str, str]]:
        """
        Resolve column references from the FROM clause.
        Returns: column_name -> (source_unique_id, column_name)
        """
        refs: dict[str, tuple[str, str]] = {}
        from_expr = select.find(exp.From)
        if not from_expr:
            return refs

        for tbl in from_expr.find_all(exp.Table):
            uid = self._resolve_table_uid(tbl)
            if uid and uid in self.source_tables:
                node = self.source_tables[uid]
                alias = tbl.alias or tbl.name
                for col_name in node.columns:
                    refs[col_name] = (uid, col_name)
                    refs[f"{alias}.{col_name}"] = (uid, col_name)

        return refs

    def _resolve_joins(self, select: exp.Select) -> dict[str, tuple[str, str]]:
        """Resolve column references from JOIN clauses."""
        refs: dict[str, tuple[str, str]] = {}

        for join in select.find_all(exp.Join):
            tbl = join.find(exp.Table)
            if not tbl:
                continue
            uid = self._resolve_table_uid(tbl)
            if uid and uid in self.source_tables:
                node = self.source_tables[uid]
                alias = tbl.alias or tbl.name
                for col_name in node.columns:
                    refs[col_name] = (uid, col_name)
                    refs[f"{alias}.{col_name}"] = (uid, col_name)

        return refs

    def _resolve_table_uid(self, tbl: exp.Table) -> str | None:
        """Resolve a sqlglot Table node to a unique_id."""
        # Try alias first
        alias = tbl.alias or tbl.name
        if alias in self._name_to_uid:
            uid = self._name_to_uid[alias]
            if uid in self.source_tables:
                return uid

        # Try the full name
        table_name = tbl.name
        if table_name in self._name_to_uid:
            uid = self._name_to_uid[table_name]
            if uid in self.source_tables:
                return uid

        # Try partial match
        clean = table_name.strip('"[]`')
        if clean in self._name_to_uid:
            uid = self._name_to_uid[clean]
            if uid in self.source_tables:
                return uid

        # Try segments of the unique_id
        for name_key, uid in self._name_to_uid.items():
            if name_key == clean or clean in uid:
                if uid in self.source_tables:
                    return uid

        return None

    def _resolve_expression(
        self,
        expr: exp.Expression,
        source_refs: dict[str, tuple[str, str]],
    ) -> None:
        """
        Resolve a single SELECT expression and emit ColumnLineage records.
        """
        # Extract alias if present
        alias = ""
        inner = expr
        if isinstance(expr, exp.Alias):
            alias = expr.alias
            inner = expr.this

        target_name = alias or self._expr_to_string(inner)
        transform_str = self._expr_to_string(inner)
        source_cols = self._find_source_columns(inner, source_refs)

        for (src_uid, src_col) in source_cols:
            self.lineage.append(ColumnLineage(
                source_column=f"{src_uid}.{src_col}",
                target_column=target_name,
                transformation=transform_str,
            ))

    def _find_source_columns(
        self,
        expr: exp.Expression,
        source_refs: dict[str, tuple[str, str]],
    ) -> list[tuple[str, str]]:
        """Find all source column references in an expression."""
        results: list[tuple[str, str]] = []

        for col in expr.find_all(exp.Column):
            col_name = col.name
            table_name = col.table

            # Direct column match
            if col_name in source_refs:
                results.append(source_refs[col_name])
                continue

            # Table.column match
            if table_name:
                key = f"{table_name}.{col_name}"
                if key in source_refs:
                    results.append(source_refs[key])
                    continue

            # If the column is a function argument, still try to trace it
            if isinstance(col.parent, exp.Func):
                if col_name in source_refs:
                    results.append(source_refs[col_name])

        return results

    def _expr_to_string(self, expr: exp.Expression) -> str:
        """Convert a sqlglot expression back to a readable string."""
        try:
            return expr.sql(dialect="spark")
        except Exception:
            try:
                return expr.sql()
            except Exception:
                return str(expr)


def extract_sql_lineage(
    node: TableNode,
    graph: LineageGraph,
) -> dict[str, list[tuple[str, str]]]:
    """
    Extract column-level lineage for a single TableNode from its compiled SQL.

    Returns:
        Dict mapping target column names to list of (source_table_uid, source_col) tuples.
    """
    if not node.compiled_sql.strip():
        return {}

    # Collect ALL ancestor nodes (not just direct depends_on) so SQL
    # table references resolve correctly even when intermediate models sit between
    # a model and its ultimate sources.
    source_tables: dict[str, TableNode] = {}
    for dep_uid in graph.ancestors(node.unique_id):
        dep_node = graph.get_node(dep_uid)
        if dep_node:
            source_tables[dep_uid] = dep_node

    extractor = ColumnExtractor(node.compiled_sql, source_tables)
    extractor.extract()

    # Build column_deps dict
    column_deps: dict[str, list[tuple[str, str]]] = {}
    for lineage_record in extractor.lineage:
        target = lineage_record.target_column
        if target not in column_deps:
            column_deps[target] = []

        src = lineage_record.source_column
        if "." in src:
            src_table, src_col = src.rsplit(".", 1)
            entry = (src_table, src_col)
            if entry not in column_deps[target]:
                column_deps[target].append(entry)

    return column_deps


def enrich_graph_with_lineage(graph: LineageGraph) -> None:
    """
    Enrich all model nodes in the graph with column-level lineage
    extracted from their compiled SQL.
    """
    for _uid, node in graph._node_data.items():
        if node.resource_type != "model" or not node.compiled_sql.strip():
            continue

        column_deps = extract_sql_lineage(node, graph)
        node.column_deps = column_deps

        # Update ColumnNode.source_columns
        for target_col, sources in column_deps.items():
            if target_col in node.columns:
                node.columns[target_col].source_columns = [
                    f"{t}.{c}" for t, c in sources
                ]


def get_column_lineage(
    node: TableNode,
    graph: LineageGraph,
) -> list[ColumnLineage]:
    """Get all column lineage records for a TableNode."""
    if not node.compiled_sql.strip():
        return []

    source_tables: dict[str, TableNode] = {}
    for dep_uid in graph.ancestors(node.unique_id):
        dep_node = graph.get_node(dep_uid)
        if dep_node:
            source_tables[dep_uid] = dep_node

    extractor = ColumnExtractor(node.compiled_sql, source_tables)
    return extractor.extract()
