import pandas as pd

# Apply patch for openpyxl
try:
    import openpyxl.descriptors.base
    orig_set = openpyxl.descriptors.base.Typed.__set__
    def patched_set(self, instance, value):
        try: orig_set(self, instance, value)
        except TypeError: pass
    openpyxl.descriptors.base.Typed.__set__ = patched_set
    
    import openpyxl.styles.named_styles
    orig_init = openpyxl.styles.named_styles._NamedCellStyle.__init__
    def patched_init(self, *args, **kwargs):
        if 'builtInId' in kwargs:
            kwargs['builtinId'] = kwargs.pop('builtInId')
        orig_init(self, *args, **kwargs)
    openpyxl.styles.named_styles._NamedCellStyle.__init__ = patched_init
except Exception:
    pass

df_hc = pd.read_excel('downloaded_headcount.xlsx', engine='openpyxl', header=None)
# Find the row that contains 'Cad.' or 'Nome'
header_idx = None
for idx, row in df_hc.iterrows():
    if row.astype(str).str.contains('Cad.', na=False).any() or row.astype(str).str.contains('Nome', na=False).any():
        header_idx = idx
        break

if header_idx is not None:
    df_hc = pd.read_excel('downloaded_headcount.xlsx', engine='openpyxl', header=header_idx+1) # actually it would be header_idx if it's 0-indexed in excel but read_excel is 0-indexed rows
    # let's just use skiprows
    df_hc = pd.read_excel('downloaded_headcount.xlsx', engine='openpyxl', skiprows=header_idx)
    # clean column names
    print("Cleaned Columns:")
    print(df_hc.columns.tolist())
    
    # drop empty columns
    df_hc = df_hc.dropna(axis=1, how='all')
    print("Cleaned Columns (after dropna):")
    print(df_hc.columns.tolist())
    print(df_hc.head(3).to_string())
else:
    print("Could not find header row.")
