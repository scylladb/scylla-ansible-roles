#!/usr/bin/env python3

import argparse
import re
import subprocess

class DepFinder(object):

    pregexp = re.compile(': ([a-z0-9+-\.]+) \(= ([a-f0-9-\.]+)\)')

    def scylla_dependencies(self, package, version):
        p = subprocess.run('apt depends '+package+"="+version + " | grep \"Depends:\" | grep scylla",
                           capture_output=True, shell=True, executable="/bin/bash")
        data = p.stdout.splitlines()
        filtereddata = {}
        for i in data:
            m = self.pregexp.search(str(i))
            if (m is not None) and (len(m.groups()) == 2):
                filtereddata[m.group(1)] = m.group(2)
        return filtereddata

    def __init__(self, package, version):
        self.dep_set = {}
        self.deps_recurse(self.dep_set, package, version)

    def deps_recurse(self, s, package, version):
        deps = self.scylla_dependencies(package, version)
        for i in deps:
            if i not in s.keys():
                s[i] = deps[i]
                self.deps_recurse(s, i, deps[i])

def main():
    parser = argparse.ArgumentParser(
        description='Find recursive dependencies of scylla packages')
    parser.add_argument('pkg', help='package to resolve dependencies')
    parser.add_argument('-v', '--version', dest="v",
                        help='version of package')
    args = parser.parse_args()
    df = DepFinder(args.pkg, args.v)
    deps = df.dep_set
    for i in deps:
        print(i + "=" + deps[i])

if __name__ == '__main__':
    main()
