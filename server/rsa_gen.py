#!/usr/bin/python3

import rsa

(pub_key,priv_key) = rsa.newkeys(1024)

f = open('key','w+')
f.write('----------pub_key------------\n')
f.write(pub_key.save_pkcs1().decode('utf8'))
f.write('\n\n')


f.write('----------priv_key------------\n')
f.write(priv_key.save_pkcs1().decode('utf8'))
f.write('\n\n')

