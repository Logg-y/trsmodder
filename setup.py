import os
import shutil
import time
import zipfile

if __name__ == "__main__":

	if os.path.isdir("build"):
		shutil.rmtree("build")
	if os.path.isdir("dist"):
		shutil.rmtree("dist")
	if os.path.isdir("trsmodder"):
		shutil.rmtree("trsmodder")
	os.system("pyinstaller trsmodder.py --onefile")
	# ugly for permissions
	time.sleep(10)
	os.rename("dist", "trsmodder")
	shutil.copy("LICENSE", "trsmodder/LICENSE")
	shutil.copy("readme.txt", "trsmodder/readme.txt")
	shutil.copy("readme.md", "trsmodder/readme.md")
	shutil.copy("changelog.txt", "trsmodder/changelog.txt")
	shutil.copy("dom4magicpaths.trsm", "trsmodder/dom4magicpaths.trsm")
	shutil.copytree("dom4magicpaths", "trsmodder/dom4magicpaths")

	zipf = zipfile.ZipFile("trsmodder.zip", "w", zipfile.ZIP_DEFLATED)
	for root, dirs, files in os.walk("trsmodder"):
		for file in files:
			zipf.write(os.path.join(root, file))
			
	zipf.close()