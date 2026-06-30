import pandas as pd
import sys

def analyze_excel(file_path):
    with open('psv_analysis.txt', 'w', encoding='utf-8') as f:
        try:
            xls = pd.ExcelFile(file_path)
            f.write(f"File: {file_path}\n")
            f.write(f"Sheet Names: {xls.sheet_names}\n\n")
            
            for sheet in xls.sheet_names:
                f.write(f"==================== Sheet: {sheet} ====================\n")
                df = pd.read_excel(xls, sheet_name=sheet)
                f.write(f"Shape: {df.shape}\n")
                f.write("Columns:\n")
                for col in df.columns:
                    f.write(f"  - {col}\n")
                
                f.write("\nFirst 15 Rows:\n")
                f.write(df.head(15).to_string() + "\n\n\n")
        except Exception as e:
            f.write(f"Error: {e}\n")

if __name__ == '__main__':
    analyze_excel(r'D:\İş\Çalışan programlar\@Güncelleme\psv sizing .xls')
