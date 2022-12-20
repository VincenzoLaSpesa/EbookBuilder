import pathlib
import os
from subprocess import check_output
from MarkdownPP import MarkdownPP
import time
import yaml
import urllib
from ftfy import fix_encoding
import shutil
import re 
from PIL import Image

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


'''
Applies a chain of filters to the input file, save it to the output file
'''
def clean_latex_source(inputFile: str, outputFile: str):

  def custom_unicodes(line: str) -> list:
      unicodes=[['∙', ' $ \cdot $  ']]
      changed= False
      for pattern in unicodes:
        if pattern[0] in line:
          line= line.replace(pattern[0], pattern[1])
          changed = True
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
    return line, changed

  def convert_gif(line:str) -> list:
    if '.gif}' in line:
              regex = r"{([^}]+)}"
              matches = [ x[1] for x in re.finditer(regex, line)]
              for m in matches:
                if '.gif' in m:
                  fullname = os.path.abspath(m)
                  print("Converting",fullname)        
                  outname = os.path.basename(fullname) + ".jpg"
                  im = Image.open(fullname).convert('RGB')
                  output_path = pathlib.Path(os.path.abspath("./out/"+outname)).as_posix()
                  im.save(output_path)
                  line= line.replace(m, output_path) 
              return line, True
    return line, False  


  filter_chain= [resize_images, convert_gif, custom_unicodes]
  
  with open(inputFile, "rt",encoding="utf8") as fin:
    with open(outputFile, "wt",encoding="utf8") as fout:
      for line in fin:
        line=line.encode('ascii',errors='ignore').decode()
        for f in filter_chain:
          line, changed = f(line)
          if changed:
            print("->", line)
        fout.write(line)


def generate_documents(infile: str, outfile: str, language: str, template: str):
  clean_fucked_utf8_file(infile)
  print("Generating", language)
  base=f"pandoc --metadata-file=metadata.yaml --metadata=lang:{language} --from=markdown"
  run(f"{base} -s -t latex --template {template} -i {infile} -o {infile}_original.tex")
  run(f"{base} -i {infile} -o {outfile}.epub")
  run(f"{base} -i {infile} -o {outfile}.odt")
  clean_latex_source(infile+'_original.tex', "./out/"+infile+'.tex')
  print(f"Done! You can find the '{language}' book at ./{outfile}")
  return [f"{outfile}.epub", f"{outfile}.odt", "./out/"+infile+'.tex',infile+'_original.tex' ]


def escape(text: str) -> str:
  text = text.replace(' ', '_').replace(',', '_')
  return urllib.parse.quote(text, safe='')

def generate(title: str, language: str, template: str, fileList: list):
  name = escape(title)
  with open(name+".mdPP", "w",encoding="utf8") as ppfile:
    if os.path.isfile("README.md"):
      f = open('README.md', "r",encoding="utf8")
      ppfile.write(f.read())


    ppfile.write(f"# {title}\r\n")
        
    for fname in fileList:
      print(fname)
      ppfile.write(f"\r\n!INCLUDE \"{fname}\", 2\r\n --- \r\n")
    ppfile.write(f"Build {time.ctime()}\r\n")
  
  infile = open(name+".mdPP", "r",encoding="utf8")
  outfile = open(name+".md", "w", encoding="utf8")
  MarkdownPP(input=infile, modules=['include', 'toc'], output=outfile)
  infile.close()
  outfile.close()
  artifacts = generate_documents(name+".md",name, language, template)
  
  for a in artifacts:
    if not a.startswith('./out/'):
      shutil.move(a, "./out/"+a)
  
# main
os.chdir("./data")
import os

if not os.path.exists('out'):
   os.makedirs('out')

metadata={}
with open('metadata.yaml') as file:
    metadata = yaml.safe_load(file)

flist=pathlib.Path('.').glob('*.md')
generateUmls("./data", "*.puml", "./img")

generate(metadata['title'], metadata['language'], metadata['template'],flist)

