# CSV Analysis Guide

## Methodology

When analyzing CSV data, follow this approach:

### Numeric Columns
- Calculate mean, median, standard deviation
- Identify outliers (values > 2 std deviations from mean)
- Note the range (min to max)

### Categorical Columns
- Count unique values
- Identify the most common values (top 5)
- Flag columns with very high cardinality (>50% unique)

### Missing Values
- Report percentage of missing values per column
- Flag columns with >20% missing as potentially unreliable

### Correlations
- For numeric column pairs, note strong correlations (|r| > 0.7)
- Flag potential multicollinearity issues
