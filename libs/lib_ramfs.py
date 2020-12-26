# A ramFS designed specifically for sonnet-py
# Ultrabear - 2020

import io

class ram_filesystem:

    def __init__(self):
        self.directory_table = {}
        self.data_table = {}

    def __enter__(self):
        return self

    def mkdir(self, make_dir):

        # Make fs list
        make_dir = make_dir.split("/")

        # If the current dir doesnt exist then create it
        if not(make_dir[0] in self.directory_table.keys()):
            self.directory_table[make_dir[0]] = ram_filesystem()

        # If there is more directory left then keep going
        if len(make_dir) > 1:
            return self.directory_table[make_dir[0]].mkdir("/".join(make_dir[1:]))
        else:
            return self

    def remove_f(self, remove_item):

        remove_item = remove_item.split("/")
        if len(remove_item) > 1:
            return self.directory_table[remove_item[0]].remove_f("/".join(remove_item[1:]))
        else:
            try:
                del self.data_table[remove_item[0]]
                return self
            except KeyError:
                raise FileNotFoundError("File does not exist")

    def read_f(self, file_to_open):

        file_to_open = file_to_open.split("/")
        try:
            if len(file_to_open) > 1:
                return self.directory_table[file_to_open[0]].read_f("/".join(file_to_open[1:]))
            else:
                return self.data_table[file_to_open[0]]
        except KeyError:
            raise FileNotFoundError("File does not exist")

    def create_f(self, file_to_write):

        file_to_write = file_to_write.split("/")
        if len(file_to_write) > 1:
            try:
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]))
            except KeyError:
                self.mkdir("/".join(file_to_write[:-1]))
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]))
        else:
            self.data_table[file_to_write[0]] = io.BytesIO()

        return self.data_table[file_to_write[0]]

    def tree(self):
        self.internal_tree(0)

    def internal_tree(self, recursion_levels):

        for i in self.data_table.keys():
            print(f"F {recursion_levels*'| '}{i}")
        for i in self.directory_table.keys():
            print(f"D {recursion_levels*'| '}{i}")
            self.directory_table[i].internal_tree(recursion_levels+1)


