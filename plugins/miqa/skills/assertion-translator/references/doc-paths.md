# MIQA guidance paths

Load only the pages needed for the translation from `$MIQA_DOCS_BASE_URL/<path>`. If
`MIQA_DOCS_BASE_URL` is not set, ask the user to set it and stop. Keep the base URL and its share
credential out of the skill.

| Question | Path |
| --- | --- |
| Core assertion fields and check type selection | `building-tests/writing-assertions/overview.md` |
| How stat, query, relationship, and static decide results | `building-tests/writing-assertions/assertion-syntax.md` |
| Dataset scope, workflow scope, and debug overrides | `building-tests/writing-assertions/advanced-assertion-parameters.md` |
| File pattern and antipattern matching | `building-tests/writing-assertions/common-parameters/file-based-test-parameters.md` |
| Tabular parsing parameters | `building-tests/writing-assertions/common-parameters/common-file-parsing-and-tabular-parameters.md` |
| Expression-based checks and shared fields | `building-tests/writing-assertions/assertion-categories/expression-based-tests.md` |
| Check types by data shape | `building-tests/writing-assertions/assertion-categories/assertion-categories-by-data-type.md` |
| Declarative and comparative methods | `building-tests/writing-assertions/assertion-categories/assertion-categories-by-method.md` |
| Rename, cast, map, drop, and filter transforms | `building-tests/writing-assertions/advanced-methods/transforms-reshaping-and-filtering-tabular-data.md` |
| Chart type and chart value shapes | `building-tests/writing-assertions/advanced-methods/adding-visual-charts-with-chart_config.md` |
| Column-specific flex comparison conditions | `building-tests/writing-assertions/advanced-methods/conditions-advanced-comparison-logic.md` |
| Multi-file stat reshaping and comparison | `building-tests/writing-assertions/advanced-methods/multi-file-query-multi_file_query.md` |
| JSON and MDO path rules with tolerance | `building-tests/writing-assertions/advanced-methods/rules-configuration-for-json-based-comparisons.md` |
| Aggregate stats across files | `building-tests/writing-assertions/advanced-methods/aggregate-expression-based-tests.md` |
| MDO concepts and supported check types | `building-tests/writing-assertions/structured-data-and-queries/working-with-mdo.md` |
| Tabular `data.rows` operations | `building-tests/writing-assertions/structured-data-and-queries/working-with-tabular-mdos.md` |
| File collection expressions | `building-tests/writing-assertions/structured-data-and-queries/working-with-filecollection-objects.md` |
| File structure summary fields | `building-tests/writing-assertions/structured-data-and-queries/working-with-filestructure-objects.md` |
| Quick tabular columns and preview | `building-tests/writing-assertions/structured-data-and-queries/dotdict-convenience-functions.md` |
| Two-list precision, recall, F1, and Jaccard | `building-tests/writing-assertions/structured-data-and-queries/analyzers/match.md` |
| Agreement across three or more lists | `building-tests/writing-assertions/structured-data-and-queries/analyzers/overlap.md` |
| Record fields and field existence | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-records.md` |
| Filter, group, map, and select rows | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-recordlists.md` |
| Match and compare record lists | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-recordlists/comparing-recordlists.md` |
| Frequency results | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-frequencies.md` |
| Single numeric value operations | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/numeric-field-validations-miqanum.md` |
| Numeric list statistics | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-miqanumlist.md` |
| String-list membership, overlap, and patterns | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/working-with-miqastringlist.md` |
| Single-string validation and parsing | `building-tests/writing-assertions/structured-data-and-queries/miqa-data-structures/string-based-validations-miqastring.md` |
| Paired tabular MDO evaluation | `building-tests/assertion-types/tabular-files/paired-tabular-mdo-eval.md` |
