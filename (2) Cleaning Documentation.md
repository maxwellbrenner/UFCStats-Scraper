# Cleaning `event_masterlist`
---

## Overview of the `main()` Function

The `main()` function in the `(2) Cleaning event_masterlist` script processes and cleans the raw event data from `event_masterlist.csv`, preparing it for analysis. 

Here’s a breakdown of its steps:

1. **Load Data**: Reads in the CSV file `event_masterlist.csv` and loads it into a DataFrame.

2. **Clean Weight Class**: Calls `clean_weightclass()` to standardize the `weightclass` column. Entries are mapped to predefined categories, ensuring consistency across the dataset.

3. **Method of Victory Diagnostics**: Displays unique values in the `method_of_victory` column for diagnostic purposes, without making modifications.

4. **Handle No Contests and Draws**: Uses `clean_no_contest_and_draws()` to standardize the `winner` column. Cases marked as `'N/A'` are converted to `'Draw'` or `'NC'` (No Contest), based on `method_of_victory`.

5. **Clean Height and Reach**: The `clean_height_and_reach()` function is called to process the height and reach columns of both fighters, removing any non-numeric characters and converting values to floats.

6. **Validate Title Fight**: Uses `clean_title_fight()` to confirm that title fights are marked correctly. Ensures all title fights correspond to a 5-round `time_format`.

7. **Clean Time Format**: The `clean_time_format()` function standardizes the `time_format` column by extracting the number of rounds as an integer, filling any non-numeric values with `NaN`.

8. **Drop Rows with Missing Values**: The `drop_nans()` function removes rows with `NaN` values in critical columns. This step ensures that essential data is complete, making the dataset ready for analysis.

9. **Save Cleaned Data**: The cleaned DataFrame is saved as `cleaned_event_masterlist.csv`.

---

## Function Descriptions -- Ordered by Execution in `main()`

### 1. `clean_weightclass(df)`
- **Description**: Cleans the `weightclass` column by mapping entries to a standardized list based on keywords.
- **Returns**: DataFrame with a cleaned `weightclass` column, where values are standardized or marked as `NaN`.

### 2. `clean_no_contest_and_draws(df)`
- **Description**: Updates the `winner` column for cases marked as `'N/A'`, converting them to `'NC'` (No Contest) or `'Draw'` based on the `method_of_victory`.
- **Returns**: DataFrame with a cleaned `winner` column.

### 3. `clean_height_and_reach(df)`
- **Description**: Cleans `fighter_a_height`, `fighter_a_reach`, `fighter_b_height`, and `fighter_b_reach` columns by removing any non-numeric characters and converting values to floats.
- **Returns**: DataFrame with standardized height and reach values for both fighters.

### 4. `clean_title_fight(df)`
- **Description**: Validates the `title_fight` column based on `time_format`, ensuring all title fights have a 5-round format.
- **Returns**: DataFrame with validated `title_fight` values.

### 5. `clean_time_format(df)`
- **Description**: Standardizes the `time_format` column by extracting the number of rounds as an integer.
- **Returns**: DataFrame with a cleaned `time_format` column.

### 6. `drop_nans(df)`
- **Description**: Removes rows with `NaN` values in essential columns, ensuring the dataset is analysis-ready.
- **Returns**: DataFrame with missing values in critical columns removed.

---

