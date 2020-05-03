#!/usr/bin/python3
import getopt
import sys

config_path = ''

priv_key_path = ''

def main():
    argv = sys.argv[1:]
    try:
        opts,args = getopt.getopt(argv,'hc:k:',['--config=','--priv-key='])
        for opt,arg in opts:
            if opt == '-h':
                print("nat_client -c <config-file> -k <priv-key> ")
                sys.exit()
            if opt in('-c','--config'):
                config_path = arg
            if opt in('-k','--priv-key'):
                priv_key_path = arg
        print('config:{0} key :{1}'.format(config_path,priv_key_path))
    except getopt.GetoptError as e:
        print("nat_client -c <config-file> -k <priv_key> ")
        sys.exit()

if __name__ == "__main__":
    main()
    print(config_path)
    print(priv_key_path)



