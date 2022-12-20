from pathlib import Path
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

def run(cmd, echo=True, shell=True, printOutput = True):
    if echo:
        print(cmd)
    output = check_output(cmd, shell=shell).decode("utf-8") 
    if printOutput:
      print(output)
    return output


def clean_fucked_utf8_file(file: str):
  shutil.move(file, 'temp.tmp')  
  outfile = open(file, "w",encoding="utf8")
  with open("temp.tmp",encoding="utf8") as fp: 
      for line in fp: 
        outfile.write(fix_encoding(line))
  os.remove("temp.tmp")


def substituteinfiles(target, substitution, inputfile, outputfile):
  fin = open(inputfile, "rt")
  fout = open(outputfile, "wt")
  for line in fin:
    fout.write(line.replace(target, substitution))
  fin.close()
  fout.close()

def clean_latex_source(fname: str):
  pattern=[r'\includegraphics{./img/',r'\includegraphics[width=0.9\textwidth]{../img/']
  fin = open(fname, "rt")
  fout = open('./build/'+fname, "wt")
  for line in fin:
    if pattern[0] in line:
      line= line.replace(pattern[0], pattern[1])
      # converting gif
      if '.gif}' in line:
        regex = r"{([^}]+)}"
        matches = [ x[1] for x in re.finditer(regex, line)]
        for m in matches:
          if '.gif' in m:
            print("Converting",m)        
            outname = os.path.basename(m) + ".jpg"
            im = Image.open(m[1:]).convert('RGB')
            im.save("./build/"+outname)
            line= line.replace(m, outname)

    fout.write(line)
  fin.close()
  fout.close()


def generate_documents(infile: str, outfile: str, language: str, template: str):
  clean_fucked_utf8_file(infile)
  print("Generating", language)
  run(f"pandoc --metadata-file=metadata.yaml --metadata=lang:{language} -f markdown -s -t latex --template {template} -i {infile} -o {infile}.tex")
  run(f"pandoc --metadata-file=metadata.yaml --metadata=lang:{language} --from=markdown -i {infile} -o {outfile}")
  run(f"pandoc --metadata-file=metadata.yaml --metadata=lang:{language} --from=markdown -i {infile} -o {outfile}.odt")
  clean_latex_source(infile+'.tex')
  print(f"Done! You can find the '{language}' book at ./{outfile}")

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
  generate_documents(name+".md",name+".epub", language, template)

# main
os.chdir("./data")
metadata={}
with open('metadata.yaml') as file:
    metadata = yaml.safe_load(file)

flist=Path('.').glob('*.md')

generate(metadata['title'], metadata['language'], metadata['template'],flist)

