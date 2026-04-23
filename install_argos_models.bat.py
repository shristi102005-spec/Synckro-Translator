import os
import argostranslate.package

# Path to your Downloads folder
downloads_folder = r"C:\Users\Acer\Downloads"

# Loop through all files in Downloads
for file in os.listdir(downloads_folder):
    if file.endswith(".argosmodel"):
        full_path = os.path.join(downloads_folder, file)
        print(f"Installing {file}...")
        try:
            argostranslate.package.install_from_path(full_path)
            print(f"{file} installed successfully ✅")
        except Exception as e:
            print(f"❌ Failed to install {file}: {e}")

print("All Argos models processed.")
import argostranslate.translate
langs = argostranslate.translate.get_installed_languages()
print([lang.code for lang in langs])


