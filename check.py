
from time import sleep,time
from platform import system
from os import path,listdir,popen,remove
from time import ctime
from shutil import copytree,copy,rmtree
from json import loads,dumps
from threading import Thread
from hashlib import sha256

# 默认参数
default_values = {
    "checkDir" : "/var/www/html",
    "logDir" : "/tmp",
    "backDir" : "/tmp/" + ctime().replace(" ","_") + ".bak",
    "logFileName" : ctime().replace(" ","_") + ".log",
    "hashFile":ctime().replace(" ","_") + ".hash",
    "timeSec" : 2,
    "timeMin" : 1
}

# 检查文件目录的文件字典
dir_files = {
    "dir":[],
    "files":[]
}

# 兼容windows
find_files = {
    "dir" : [],
    "files" : []
}

# 是否输出信息
isOutput = 0

# 线程池
thread_pool = {
    'checkFileHash': None,
    'checkNewFile' : None
}

# 兼容windows
def findFiles(dir):

    global find_files

    fileList = listdir(dir)

    for fileName in fileList:
        absFile = path.realpath(path.join(dir, fileName))
        if (path.isdir(absFile)):
            findFiles(absFile)
            find_files['dir'].append(absFile)
        elif (path.isfile(absFile)):
            if (time() - path.getmtime(absFile) < default_values['timeMin'] * 60):
                find_files['files'].append(absFile)

# 进行备份操作
def getBackup(sDir,bDir):

    try:
        copytree(sDir,bDir)
    except Exception as e:
        print("[-] -> 无法成功备份对应目录文件！",e)
        exit(1)

# 日志文件写入
def logFileWrite(s):

    # 若回显开启则回显
    if(isOutput):
        print(s)
    # 写入日志
    with open(path.realpath(logDir + "/" + logFileName),"a") as f:
        f.write(s + "\n")

# 获取目录以及文件
def getAllFiles(dir):

    global dir_files

    fileList = listdir(dir)

    for fileName in fileList:
        absFile = path.realpath(path.join(dir, fileName))
        if (path.isdir(absFile)):
            getAllFiles(absFile)
            dir_files['dir'].append(absFile)
        elif (path.isfile(absFile)):
            dir_files['files'].append(absFile)

# 获取单个文件hash
def getFileHash(fileName):
    hash = sha256()
    with open(fileName,"rb") as f:
        hash.update(f.read())
    return hash.hexdigest()

# 获取检查目录的hash记录
def getFilesHash():

    global dir_files

    result_dict = {}

    for fileName in dir_files['files']:
        result_dict[fileName] = [fileName,path.realpath(path.realpath(backDir) + "/" + fileName[len(path.realpath(checkDir)):]),getFileHash(fileName = fileName)]

    for dirName in dir_files['dir']:
        result_dict[dirName] = [dirName,path.realpath(path.realpath(backDir) + "/" + dirName[len(path.realpath(checkDir)):])]

    result_dict_json = dumps(result_dict)

    with open(path.join(logDir,hashFile),"w") as f:
        f.write(result_dict_json)

# 检查文件hash
def checkFileHash():

    global hashFile

    while True:
        try:
            with open(path.realpath(logDir + "/" + hashFile), "r") as f:
                result_dict = loads(f.read())

            # 对目录操作
            for dirName in dir_files['dir']:
                # 目录被删除
                if(not path.exists(dirName)):
                    logFileWrite("[O] 输出 { 来自检查文件hash } -> [ " + dirName + " ] 目录被删除！")
                    logFileWrite("[O] 输出 { 来自检查文件hash } -> 尝试恢复目录~ \n")
                    if(dirName in result_dict.keys()):
                        copytree(result_dict[dirName][1],result_dict[dirName][0])
                    else:
                        logFileWrite("[O] 输出 { 来自检查文件hash } -> [ " + dirName + " ] 目录恢复失败！")

            # 对文件操作
            for fileName in dir_files['files']:
                # 文件被删除
                if(not path.exists(fileName)):
                    logFileWrite("[O] 输出 { 来自检查文件hash } -> [ " + fileName + " ] 文件被删除！")
                    logFileWrite("[O] 输出 { 来自检查文件hash } -> 尝试恢复文件~ \n")
                    if(fileName in result_dict.keys()):
                        copy(result_dict[fileName][1], result_dict[fileName][0])
                    else:
                        logFileWrite("[O] 输出 { 来自检查文件hash } -> [ " + fileName + " ] 文件恢复失败！")
                    continue

                if(getFileHash(fileName = fileName) != result_dict[fileName][2]):

                    logFileWrite("[O] 输出 { 来自检查文件hash } -> [ " + fileName + " ] 文件hash不匹配！")
                    logFileWrite(f"------ {getFileHash(fileName = fileName)} <> {result_dict[fileName][2]} ------")
                    logFileWrite("[O] 输出 { 来自检查文件hash } -> 尝试替换~ \n")

                    remove(result_dict[fileName][0])
                    copy(result_dict[fileName][1], result_dict[fileName][0])

        except Exception as e:
            logFileWrite("[-] 警告 { 来自检查文件hash } -> " + e.__str__())
        finally:
            sleep(default_values["timeSec"])

# 检查是否存在新文件增加
def checkNewFile():

    global checkDir,hashFile

    while True:
        try:
            with open(path.realpath(logDir + "/" + hashFile), "r") as f:
                result_dict = loads(f.read())

            result = []
            # 兼容
            if(system() == "Linux"):

                with popen("find " + path.realpath(checkDir) + " -name \"*\" -mmin " + default_values['timeMin'].__str__() + " -type f 2>/dev/null", "r") as p:
                    result = p.read().split("\n")

                with popen("find " + path.realpath(checkDir) + " -name \"*\" -type d 2>/dev/null", "r") as p:
                    result.extend(p.read().split("\n"))


            elif(system() == "Windows"):

                global find_files
                find_files = {"dir":[],"files":[]}
                findFiles(path.realpath(checkDir))

                for each in find_files["dir"]:
                    result.append(each)
                for each in find_files["files"]:
                    result.append(each)

            # 若结果为空则跳过
            if(len(result) == 1 and result[0] == ''):
                continue

            # 剔除自身
            if(path.realpath(checkDir) in result):
                result.remove(path.realpath(checkDir))

            for fileName in result:
                if (path.realpath(fileName) not in result_dict.keys() and fileName != ''):
                    logFileWrite("[O] 输出 { 来自是否存在新文件增加 } -> [ " + fileName + " ] 文件/目录被添加！")
                    # 删除被添加的文件
                    if(path.isfile(path.realpath(fileName))):
                        remove(path.realpath(fileName))
                    # 删除被添加的目录
                    if(path.isdir(path.realpath(fileName))):
                        rmtree(path.realpath(fileName))

        except Exception as e:
            logFileWrite("[-] 警告 { 来自是否存在新文件增加 } -> " + e.__str__())
        finally:
            sleep(default_values["timeSec"])





# 检查参数
def checkParams(params):

    global checkDir,logDir,logFileName,hashFile,backDir

    # 检查需检查的目录参数
    if (not path.isdir(params['checkDir']) or params['checkDir'] == ""):
        print("[*] -> 需要检查的目录不存在！默认设为 " + default_values['checkDir'])
        checkDir = default_values['checkDir']
    else:
        checkDir = params['checkDir']

    # 检查日志目录参数
    if (not path.isdir(params['logDir']) or params['logDir'] == ""):
        print("[*] -> 存储日志目录不存在！默认设为 " + default_values['logDir'])
        logDir = default_values['logDir']
    else:
        logDir = params['logDir']

    # 检查日志文件名称参数
    if (params['logFileName'] == ""):
        print("[*] -> 日志名称为空！默认设为 " + default_values['logFileName'])
        logFileName = default_values['logFileName']
    else:
        logFileName = params['logFileName']

    # 检查hash文件位置参数
    if (params['hashFile'] == ""):
        print("[*] -> hash文件位置为空！默认设为 " + default_values['hashFile'])
        hashFile = default_values['hashFile']
    else:
        hashFile = params['hashFile']

    # 检查备份目录参数
    if (params['backDir'] == ""):
        print("[*] -> 备份目录名称为空！默认设为 " + default_values['backDir'])
        backDir = default_values['backDir']
    else:
        backDir = params['backDir']

    # 获取目录和文件
    getAllFiles(checkDir)


if __name__ == '__main__':

    # 交互过程

    while True:
        try:
            print("===== 欢迎使用Morouu文件检查玩意 =====")

            inputParams = {}

            # 获取输入
            inputParams['checkDir'] = input("[*] 请输入需检查的目录(留空则使用默认值) -> ")
            inputParams['logDir'] = input("[*] 请输入日志存储的目录(留空则使用默认值) -> ")
            inputParams['logFileName'] = input("[*] 请输入日志文件名称(留空则使用默认值) -> ")
            inputParams['hashFile'] = input("[*] 请输入hash文件存储位置(留空则使用默认值) -> ")
            inputParams['backDir'] = input("[*] 请输入备份目录(留空则使用默认值) -> ")

            # 检查参数
            checkParams(inputParams)

            # 可选部分

            # 备份
            isBackup = input("[**] 是否进行备份(y/N) -> ")
            if(isBackup.upper() == 'Y'):
                global checkDir,backDir
                getBackup(sDir = checkDir,bDir = backDir)

            # 生成hash
            isHash = input("[**] 是否生成hash文件(y/N) -> ")
            if (isHash.upper() == 'Y'):
                getFilesHash()

            # 回显
            isOutput = input("[**] 是否回显(y/N) -> ")
            if(isOutput == 'Y'):
                isOutput = 1

            # 开启线程
            if(thread_pool['checkNewFile'] == None and thread_pool['checkFileHash'] == None):
                thread_pool['checkFileHash'] = Thread(target = checkFileHash)
                thread_pool['checkNewFile'] = Thread(target = checkNewFile)
                for each in thread_pool.values():
                    each.setDaemon(daemonic = True)
                    each.start()

                for each in thread_pool.values():
                    each.join()
            else:
                while True:
                    sleep(default_values["timeSec"])

        except KeyboardInterrupt:
            isExit = input("[*] 是否退出(y/N) -> ")
            if(isExit.upper() == 'Y'):
                print("Bye~~~")
                exit(0)
