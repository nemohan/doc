
import os, os.path
import codecs
import re

path=r"C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images"
test_data= r"![1584877827965](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1584877827965.png)"

default_store_path = "./img"

def get_old_img_files():
    table ={} 
    for dirpath,dirnames,filenames in os.walk(path):
        for i in range(0, len(filenames)):
            name, _ = os.path.splitext(filenames[i])
            table[name] = os.path.join(dirpath, filenames[i])
        return table

            
def update_img_pos(path, old_imgs):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith(".md"):
                continue
            print(f)
            with codecs.open(os.path.join(dirpath, f), encoding="utf-8") as file_handler:
                for line in file_handler.readlines():
                    m = re.match(r"^!\[([0-9]*)\]", line)
                    if m:
                        print(f, line, flush=True)

        for dir in dirnames:
            update_img_pos(os.path.join(dirpath,dir))

    
if __name__ == "__main__":
    """
    m = re.match("^!\[([0-9]*)\]", test_data)
    if m:
        print("ok")
        print(m.group(1))
    print(m)
    """
    files = get_old_img_files()
    print(files)
    #update_img_pos("./", files)

   
