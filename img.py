
import os, os.path
import codecs
import re
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

path=r"C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images"
test_data= r"![1584877827965](C:\Users\lenovo\AppData\Roaming\Typora\typora-user-images\1584877827965.png)"

default_store_path = "./img"

pjoin = os.path.join
def get_old_img_files():
    table ={} 
    for dirpath,dirnames,filenames in os.walk(path):
        for i in range(0, len(filenames)):
            name, _ = os.path.splitext(filenames[i])
            #table[name] = os.path.join(dirpath, filenames[i])
            table[name] = filenames[i]
            return table

            
def walk_dir(path, handler):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if handler:
                handler(dirpath, f)
        for dir in dirnames:
            walk_dir(os.path.join(dirpath,dir), handler)

def clean(dirpath, filename):
    if not filename.endswith(".backup"):
        return
    filename = os.path.join(dirpath, filename)
    os.remove(filename)
    print("remove %s" % filename) 
    
def clean_backup():
    walk_dir("./", clean)
    print("clean done\n")

def update_img_pos(path, old_imgs, level):
    print("enter %s\n" % path) 
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if not f.endswith(".md"):
                continue

            backup_file_name = pjoin(dirpath, f +".backup")
            print("new file %s\n" % backup_file_name, flush=True)
            backup_file = codecs.open(backup_file_name, "x", encoding="utf-8")
            with codecs.open(pjoin(dirpath, f), encoding="utf-8") as file_handler:
                for line in file_handler.readlines():
                    m = re.match(r"^!\[([0-9]*)\]", line)
                    if m and m.group(1) in old_imgs:
                        key = m.group(1)
                        new_path = "../" * level
                        new_path = pjoin(pjoin(new_path, "./img"), old_imgs[key])
                        new_line = "![%s](%s)" % (key, new_path)
                        backup_file.write(new_line)

                    else:
                        backup_file.write(line)

            backup_file.close()

        level += 1
        for dir in dirnames:
            print("===%s===\n" % dir)
            update_img_pos(os.path.join(dirpath,dir), old_imgs, level)

    print("leave %s\n" % path) 

    
if __name__ == "__main__":
    clean_backup()
    files = get_old_img_files()
    update_img_pos("./", files, 0)

   
