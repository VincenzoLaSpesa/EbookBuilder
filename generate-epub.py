import pathlib
import os
from subprocess import check_output
import time
import yaml
import urllib
from ftfy import fix_encoding
import shutil
import re 
from PIL import Image
import argparse
import pprint
import sys

sys.path.append("./markdown-pp")
from MarkdownPP import MarkdownPP


PLANTUML_PATH="D:\\ProgrammiPortable\\bin\\plantuml.jar"

def run(cmd, echo=True, shell=True, printOutput = True):
    if echo:
        print(cmd)
    output = check_output(cmd, shell=shell).decode("utf-8") 
    if printOutput:
      print(output)
    return output

def generateUmls(inputFolder: str, filter: str, outputFolder: str): 
    flist=pathlib.Path(inputFolder).glob(filter)
    for fname in flist:
      basename = (os.path.basename(fname).split("."))[0]
      basename_with_path=str(fname).split('.')[0]
      run(f"java -jar {PLANTUML_PATH} {fname} -tpng")
      shutil.move(basename_with_path+".png", os.path.join(outputFolder, basename+".png"))    


def clean_fucked_utf8_file(file: str):
  shutil.move(file, 'temp.tmp')  
  outfile = open(file, "w",encoding="utf8")
  with open("temp.tmp",encoding="utf8") as fp: 
      for line in fp: 
        outfile.write(fix_encoding(line))
  os.remove("temp.tmp")

def is_number(s):
    try:
        complex(s) # for int, long, float and complex
    except ValueError:
        return False

    return True


'''
Applies a chain of filters to the input file, save it to the output file
'''
def apply_filters_chain(inputFile: str, outputFile: str):

  output_folder=os.path.dirname(outputFile)

  def custom_unicodes(line: str) -> list:
      unicodes=[['∙', ' $ \cdot $  ']]
      changed= False
      for pattern in unicodes:
        if pattern[0] in line:
          line= line.replace(pattern[0], pattern[1])
          changed = True
      return line, changed

  def make_links_absolute(line: str) -> list:
    patterns=[
      r".+{([^}]+\..+)}"
    ]    
    changed= False
    for pattern in patterns:
      matches = [ x[1] for x in re.finditer(pattern, line)]
      for m in matches:
        if (not is_number(m)) and os.path.isfile(m):
          print("LTX\tFixPath\t",line.strip())
          output_path = pathlib.Path(os.path.abspath(m)).as_posix()
          line= line.replace(m, output_path)
          changed=True
    return line, changed

  def resize_images(line: str) -> list:
    patterns=[#fix huge images
      [r'\includegraphics{',r'\includegraphics[width=0.9\textwidth]{'],
      [r'\includegraphics{',r'\includegraphics[width=0.9\textwidth]{'],
    ]
    changed= False
    for pattern in patterns:
      if pattern[0] in line:
        line= line.replace(pattern[0], pattern[1])
        changed=True
        print("LTX\tFormat\t",line.strip())
    return line, changed

  def convert_gif(line:str) -> list:
    changed= False
    if '.gif}' in line:
              regex = r"{([^}]+)}"
              matches = [ x[1] for x in re.finditer(regex, line)]
              for m in matches:
                if '.gif' in m:
                  fullname = os.path.abspath(m)
                  if os.path.isfile(fullname):
                    #print("Converting",fullname)        
                    outname = os.path.basename(fullname) + ".jpg"
                    im = Image.open(fullname).convert('RGB')                  
                    output_path = pathlib.Path(os.path.abspath(os.path.join(output_folder, outname))).as_posix()
                    im.save(output_path)
                    line= line.replace(m, output_path)
                    changed=True 
                    print("CONV\t",fullname,"\t->\t",output_path)
    return line, changed  


  filter_chain= [resize_images, convert_gif, custom_unicodes, make_links_absolute]
  
  with open(inputFile, "rt",encoding="utf8") as fin:
    with open(outputFile, "wt",encoding="utf8") as fout:
      for line in fin:
        line=line.encode('ascii',errors='ignore').decode()
        for f in filter_chain:
          line, _ = f(line)
        fout.write(line)


def generate_documents(infile: str, outfile: str, language: str, template: str, outputfolder: str):
  clean_fucked_utf8_file(infile)
  print("Generating", language)
  base=f"pandoc --metadata-file=metadata.yaml --metadata=lang:{language} --from=markdown"
  run(f"{base} -s -t latex --template {template} -i {infile} -o {infile}_original.tex")
  run(f"{base} -i {infile} -o {outfile}.epub")
  run(f"{base} -i {infile} -o {outfile}.odt")
  filteredTex = os.path.join(outputfolder, infile+'.tex')
  apply_filters_chain(infile+'_original.tex', filteredTex)
  print("BUILD\t",filteredTex)
  artifacts = [f"{outfile}.epub", f"{outfile}.odt", filteredTex ,infile+'_original.tex' ]
  for a in artifacts:
    if not is_file_in_directory(a, outputFolder):
      d=os.path.join(outputfolder,a)
      print("MOVE\t",a,"\t->\t",d)
      shutil.move(a, d)



def escape(text: str) -> str:
  text = text.replace(' ', '_').replace(',', '_')
  return urllib.parse.quote(text, safe='')


def is_file_in_directory(file_path: str, directory: str) -> bool:
    file_path = os.path.abspath(file_path)
    directory = os.path.abspath(directory)
    return file_path.startswith(directory)

def generate(title: str, language: str, template: str, fileList: list, outputfolder: str):
  name = escape(title)
  with open(name+".mdPP", "w",encoding="utf8") as ppfile:
    if os.path.isfile("README.md"):
      f = open('README.md', "r",encoding="utf8")
      ppfile.write(f.read())


    ppfile.write(f"# {title}\r\n")
    ppfile.write("\r\n!TOC\r\n")
        
    for fname in fileList:
      print("ADD\t",fname)
      ppfile.write(f"\r\n!INCLUDE \"{fname}\", 2\r\n --- \r\n")
    ppfile.write(f"Build {time.ctime()}\r\n")
  
  infile = open(name+".mdPP", "r",encoding="utf8")
  outfile = open(name+".md", "w", encoding="utf8")
  c=MarkdownPP.process(input=infile, modules=['include', 'ImageRelativeToRoot'], output=outfile, encoding="UTF8") #'tableofcontents'
  infile.close()
  outfile.close()
  generate_documents(name+".md",name, language, template, outputFolder)

  pprint.pprint(c)
  print(f"Done! You can find the '{language}' book in {outputFolder}")

def check_tools():
  # first column is the command, second column is set to true if it's needed
  cmds=[
    ("pandoc -v", True),
    ("java -version", False),
    (f"java -jar \"{PLANTUML_PATH}\" -version", False)    
    ]
  
  for c in cmds:
    try:
      s=run(c[0],False,True,False)
      print(s.split('\n', 1)[0])
    except:
      print("I could not run", c[0].split()[0])
      if c[1]:
        print("the script will exit")
        return False
  print("All the mandatory tools seems available, let's start")
  return True
      


# main

if not check_tools():
  exit(False)

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--inputFolder",type=str, help="input folder", required=False)
parser.add_argument("-o", "--outputFolder",type=str, help="output folder", required=False)

args = parser.parse_args()
pprint.pprint(args)

inputFolder=os.path.abspath("./data")
outputFolder=os.path.abspath("./data/out")
blackList=set()

#inputFolder = "D:\\Codice\\Frammenti"
outputFolder="D:\\Codice\\EbookBuilder\\customoutput"


if args.inputFolder:
  inputFolder=os.path.abspath(args.inputFolder)

if args.outputFolder:
  inputFolder=os.path.abspath(args.inputFolder)

print("Generate an ebook from",inputFolder,"put the result in", outputFolder)

os.chdir(inputFolder)

if not os.path.exists(outputFolder):
   os.makedirs(outputFolder)

metadata={}
with open('metadata.yaml') as file:
    metadata = yaml.safe_load(file)

blackList.add(metadata['title']+'.md')
blackList.add(escape(metadata['title'])+'.md')

glob=[ str(x) for x in list(pathlib.Path('.').rglob('*.md'))]
flist=[ x for x in glob if not (x.startswith('./out/') or x in blackList)]
imgFolder = os.path.join(inputFolder, 'img')
generateUmls(inputFolder, "*.puml", imgFolder)

generate(metadata['title'], metadata['language'], metadata['template'],flist, outputFolder)

