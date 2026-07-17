import pandas as pd

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

df = pd.read_excel('downloaded_abs.xls', engine='openpyxl')
df = df.fillna('')
print(df.head(30).to_string())
