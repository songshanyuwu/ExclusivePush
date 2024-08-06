str = 'chr(111)+chr(112)+chr(101)+chr(110)+chr(40)+chr(39)+chr(47)+chr(118)+chr(97)+chr(114)+chr(47)+chr(119)+chr(119)+chr(119)+chr(47)+chr(115)+chr(104)+chr(116)+chr(101)+chr(114)+chr(109)+chr(47)+chr(114)+chr(101)+chr(115)+chr(111)+chr(117)+chr(114)+chr(99)+chr(101)+chr(115)+chr(47)+chr(113)+chr(114)+chr(99)+chr(111)+chr(100)+chr(101)+chr(47)+chr(108)+chr(98)+chr(106)+chr(55)+chr(57)+chr(55)+chr(46)+chr(116)+chr(120)+chr(116)+chr(39)+chr(44)+chr(39)+chr(119)+chr(39)+chr(41)+chr(46)+chr(119)+chr(114)+chr(105)+chr(116)+chr(101)+chr(40)+chr(39)+chr(98)+chr(39)+chr(41)'
str = str.replace('chr(', '').replace(')', '')
list = str.split('+')
#print(list)

str1 = ''
for i in list:
    str1 = str1 + chr(int(i))
print(str1)