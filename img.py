
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
         for f in filenames:
            name, _ = os.path.splitext(f)
            table[name] = pjoin(dirpath, f)

    return table

"""
def walk_dir(path, handler):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            if handler:
                handler(dirpath, f)
        for dir in dirnames:
            walk_dir(os.path.join(dirpath,dir), handler)

"""

def walk_dir(path, handler, *arg):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            handler(dirpath, f, *arg)

def clean(dirpath, filename,*arg):
    if not filename.endswith(".backup"):
        return
    filename = os.path.join(dirpath, filename)
    os.remove(filename)
    print("remove %s" % filename) 
    
def clean_backup():
    walk_dir("./", clean)
    print("clean done\n")


def copy_img(dst_path, src_path):
    print("copy img from %s to %s\n" %(src_path, dst_path))
    basename = os.path.basename(src_path)
    dst_file = pjoin(dst_path, basename)
    if os.path.exists(dst_file):
        return
    
    dst_file_handler = open(dst_file, "x+b")
    #wr = io.BufferedIOBase(dst_file_handler)
    with open(src_path, "rb") as file_handler:
        while True:
            buf = file_handler.read(4096)
            print("read", len(buf))
            dst_file_handler.write(buf)
            if len(buf) < 4096:
                break
            

    dst_file_handler.close()
    print("copy done\n")



def handle_img(dirpath, filename, *arg):
    if not filename.endswith(".md"):
        return

    if not arg:
        return

    old_imgs = arg[0]

    img_path = pjoin(dirpath, "${img}")
    if not os.path.exists(img_path):
        print("mkdir %s\n" % img_path)
        os.mkdir(img_path)    
    
    
    backup_file_name = pjoin(dirpath, filename +".backup")
    backup_file = codecs.open(backup_file_name, "x", encoding="utf-8")

    with codecs.open(pjoin(dirpath, filename), encoding="utf-8") as file_handler:
        for line in file_handler.readlines():
            m = re.match(r"^!\[([0-9]*)\]", line)
            if m and m.group(1) in old_imgs:
                key = m.group(1)
                copy_img(img_path, old_imgs[key])
                basename = os.path.basename(old_imgs[key])
                new_path = pjoin("./${img}", basename)
                new_line = "![%s](%s)" % (key, new_path)
                backup_file.write(new_line)
            else:
                backup_file.write(line)
        backup_file.close()

    
def update_img_pos(path, old_imgs):
    walk_dir(path, handle_img, old_imgs)

    
def usage():
    txt="""-c clean all new file
        -r replace image file path
        """
    print(txt)
    sys.exit(1)

def test_walk_dir():
    for dirpath, dirs, files in os.walk("./"):
        for d in dirs:
            print("dir:%s\n" % d)
        for f in files:
            print("file:%s\n" %f)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(sys.argv)
        usage()
    if sys.argv[1] == "-c":
        clean_backup()
        sys.exit(0)
    elif sys.argv[1] == "-r":
        clean_backup()
        files = get_old_img_files()
        update_img_pos("./", files)
    else:
        usage()

   
