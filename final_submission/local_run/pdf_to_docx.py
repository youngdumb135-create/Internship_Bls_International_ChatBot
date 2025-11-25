from pdf2docx import Converter
import os
import glob

def pdf_to_docx_conversion(pdf_location, docx_location):
    
    if not os.path.exists(pdf_location):
        print(f"Error: PDF file not found at {pdf_location}")
        return None
    
    try:
        cv = Converter(pdf_location)     
        cv.convert(docx_location)
        cv.close()
        
        print(f"Successfully converted '{pdf_location}' to '{docx_location}'.")
        return docx_location
        
    except Exception as e:
        print(f"An error occurred during conversion: {e}")
        return None

def batch_convert_pdfs(source_folder, destination_folder):
   
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
        print(f"Created destination folder: {destination_folder}")
    
    pdf_files = glob.glob(os.path.join(source_folder, "*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in the source folder: {source_folder}")
        return

    print(f"Found {len(pdf_files)} PDF files to convert.")
    
    for pdf_path in pdf_files:

        file_name = os.path.basename(pdf_path)
        base_name = os.path.splitext(file_name)[0]
        docx_path = os.path.join(destination_folder, f"{base_name}.docx")
        
        if os.path.exists(docx_path):
            print(f"Skipping '{file_name}' as '{base_name}.docx' already exists.")
            continue


        """ counter = 1
        while os.path.exists(docx_path):
            new_base_name = f"{base_name}_{counter}"
            docx_path = os.path.join(destination_folder, f"{new_base_name}.docx")
            counter += 1
 """
        pdf_to_docx_conversion(pdf_path, docx_path)
        
    print("\nBatch conversion complete.")



if __name__ == "__main__":
    source_directory = "D:\Chatbot\practice\Knowledge_Base\India\PDFs"
    destination_directory = "D:\Chatbot\practice\Knowledge_Base\India\Docx"

    batch_convert_pdfs(source_directory, destination_directory)