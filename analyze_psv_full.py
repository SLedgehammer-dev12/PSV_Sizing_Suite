import pandas as pd

def full_analysis(file_path):
    with open('psv_full_analysis.txt', 'w', encoding='utf-8') as f:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            f.write(f"\n{'='*30}\nSHEET: {sheet}\n{'='*30}\n")
            df = pd.read_excel(xls, sheet_name=sheet)
            for index, row in df.iterrows():
                row_vals = []
                for val in row:
                    if pd.notna(val) and str(val).strip() != '':
                        row_vals.append(str(val))
                if row_vals:
                    f.write(f"Row {index:03d}: {' | '.join(row_vals)}\n")

if __name__ == '__main__':
    full_analysis(r'D:\İş\Çalışan programlar\@Güncelleme\psv sizing .xls')
