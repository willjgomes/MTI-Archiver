def convert_df_to_sheet_rows(df, sheet):
    # Replace NaN values with an empty string
    df.fillna("", inplace=True) 

    headers = sheet.row_values(1)

    if (headers):
        # Add empty fields to data frame for columns that only exist in google sheet
        for col in headers:
            if col not in df.columns:
                df[col] = ""  # Add missing columns as empty
    else:
        # Add header row to sheet using the data frame columns
        headers = df.columns.tolist()
        sheet.insert_row(headers)

    # Reorder DataFrame columns to match the sheet
    df = df[headers]  # This ensures correct column alignment

    # Convert DataFrame to list of lists
    data_to_append = df.values.tolist()

    return data_to_append
