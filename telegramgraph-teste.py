#!/usr/bin/python
# -*- coding: utf-8 -*-

# Envio de gráfico por Telegram através do ZABBIX (Send zabbix alerts graph Telegram)
#
# Copyright (C) <2016>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Contacts:
# Eracydes Carvalho (Sansão Simonton) - NOC Analyst - sansaoipb@gmail.com
# Thiago Paz - NOC Analyst - thiagopaz1986@gmail.com

import json, os, re, sys, time, urllib3
import requests

if sys.version_info < (3, 0):
    import ConfigParser
    conf = ConfigParser
else:
    import configparser
    conf = configparser

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class PropertiesReaderX:
    config = None
    def __init__(self,pathToProperties):
        PropertiesReaderX.config = conf.RawConfigParser()
        PropertiesReaderX.config.read(pathToProperties)

    def getValue(self,section,key):
        # type: (object, object) -> object
        return PropertiesReaderX.config.get(section, key)

    def setValue(self,section,key):
        PropertiesReaderX.config.set(section, key)

if sys.platform.startswith('win32') or sys.platform.startswith('cygwin') or sys.platform.startswith('darwin'):  # para debug quando estiver no WINDOWS ou MAC
    path = os.path.join(os.getcwd(), "{0}")
else:
    path = "/usr/local/share/zabbix/alertscripts/"

    if not os.path.exists(path):
        path = "/usr/lib/zabbix/alertscripts/{0}"
    else:
        path = "/usr/local/share/zabbix/alertscripts/{0}"

# Zabbix settings | Dados do Zabbix #############################################################################################################
zbx_server = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'url')
zbx_user   = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'user')
zbx_pass   = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'pass')

# Graph settings | Configuracao do Grafico ######################################################################################################
graph_path = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSectionTelegram', 'path.graph') # Path where graph file will be save temporarily
height     = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'height')    # Graph height | Altura
width      = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'width')     # Graph width  | Largura

# Salutation | Saudação #########################################################################################################################
Salutation = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'salutation')
if re.search("(sim|s|yes|y)", str(Salutation).lower()):
    hora = int(time.strftime("%H"))

    if hora < 12:
        salutation = 'Bom dia'
    elif hora >= 18:
        salutation = 'Boa noite'
    else:
        salutation = 'Boa tarde'
else:
    salutation = ""

# Diretórios
# Telegram-cli path | Diretório do Telegram-cli
projeto = "telegram"
telegram_path = "{0}".format(path.format(projeto))

# Log path | Diretório do log
logName = '{0}graph-teste.log'.format(projeto)
pathLogs = path.format("log")
arqLog = "{0}".format(os.path.join(pathLogs, logName))

if not os.path.exists(pathLogs):
    os.makedirs(pathLogs)

#################################################################################################################################################
#################################################################################################################################################
#################################################################################################################################################
#################################################################################################################################################

import logging.config
import traceback

file = """{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "simple": {
            "format": "[%(asctime)s][%(levelname)s] - %(message)s"
        }
    },

    "handlers": {
        "file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "maxBytes": 5242880,
            "backupCount":5,
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "python_logging.log",
            "encoding": "utf8"
        }
    },

    "root": {
        "level": "DEBUG",
        "handlers": ["file_handler"]
    }
}
"""

arqConfig = "logging_configuration.json"
pathDefault = ""

class Log:
    @staticmethod
    def writelog(entry, pathfile, log_level):
        global pathDefault

        try:
            Log.log(entry, pathfile, log_level)
        except Exception:
            try:
                if "\\" in traceback.format_exc():
                    linha = re.search("(File)[A-Za-z0-9_\"\\\\\s:.]+", traceback.format_exc()).group()[5:].replace("\"","")
                    pathDefault = "{0}\\".format("\\".join(linha.split("\\")[:-1]))
                else:
                    linha = re.search("(File)[A-Za-z0-9_\"/\s:.]+", traceback.format_exc()).group()[5:].replace("\"", "")
                    pathDefault = "{0}/".format("/".join(linha.split("/")[:-1]))
                arquivo = open("{0}{1}".format(pathDefault, arqConfig), "w")
                arquivo.writelines(file)
                arquivo.close()
                Log.log(entry, pathfile, log_level)
            except Exception:
                pass

    @staticmethod
    def log(entry, pathfile, log_level):
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)
        logging.getLogger('suds.wsdl').setLevel(logging.CRITICAL)
        with open("{0}{1}".format(pathDefault, arqConfig), 'r+') as logging_configuration_file:
            config_dict = json.load(logging_configuration_file)
            config_dict["handlers"]["file_handler"]['filename'] = pathfile
        logging.config.dictConfig(config_dict)
        logger = logging.getLogger(__name__)
        logging.getLogger("suds").setLevel(logging.CRITICAL)
        if log_level.upper() == "INFO":
            logger.info(str(entry))
        elif log_level.upper() == "WARNING":
            logger.warning(str(entry))
        elif log_level.upper() == "CRITICAL":
            logger.critical(str(entry))
        elif log_level.upper() == "ERROR":
            logger.error(str(entry))

log = Log

def destinatarios(dest):
    destinatario = ["{0}".format(hostsW).replace(" ", "") for hostsW in dest.split(",")]

    return destinatario

def send_telegram(dest, itemType, get_graph):
    saudacao = salutation
    if saudacao:
        saudacao = salutation + " {0} \\n\\n"
    else:
        saudacao = ""

    telegram_path = "{0}".format(path.format("telegram"))
    try:
        if telegram_path.endswith('/'):
            telegram_path = telegram_path[:-1]

        os.chdir(telegram_path)
    except BaseException as e:
        log.writelog('{0}'.format(str(e)), arqLog, "WARNING")

    if re.search("(0|3)", itemType):
        try:
            graph_path = PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSectionTelegram', 'path.graph')  # Path where graph file will be save temporarily
            graph = '{0}/{1}.png'.format(graph_path, itemid)
            with open(graph, 'wb') as png:
                png.write(get_graph.content)
        except BaseException as e:
            log.writelog(
                '{1} >> An error occurred at save graph file in {0} | Ocorreu um erro ao salvar o grafico no diretório {0}'.format(
                    graph_path, str(e)), arqLog, "WARNING")
            logout_api()
            exit()

        send_msg = os.popen("""./telegram-cli -k tg-server.pub -c telegram.config -WR -U zabbix -e 'send_photo {0} {1} "{2}{3} {4}"'""".format(dest, graph, saudacao.format(dest.replace("_", " ")), subject, body)).read()

        try:
            os.remove(graph)
        except Exception as e:
            print(e)
            log.writelog('{0}'.format(str(e)), arqLog, "ERROR")

    else:
        send_msg = os.popen("""./telegram-cli -k tg-server.pub -c telegram.config -WR -U zabbix -e 'msg {0} "{1}{2} {3}"'""".format(dest, saudacao.format(dest.replace("_", " ")), subject, body)).read()

    if not 'fail' in send_msg.lower():
        print('Telegram sent successfully | Telegram enviado com sucesso ({0})'.format(dest))
        log.writelog('Telegram sent successfully | Telegram enviado com sucesso ({0})'.format(dest), arqLog, "INFO")
    else:
        error_msg = "".join(re.findall(r'FAIL: (.*?)\n', send_msg, re.I | re.DOTALL))
        print('Telegram FAIL at sending photo message | FALHA ao enviar a mensagem com gráfico pelo telegram\n%s' % error_msg)
        log.writelog('{0} >> Telegram FAIL at sending photo message | FALHA ao enviar a mensagem com gráfico pelo telegram ({1})'.format(error_msg, dest), arqLog, "ERROR")
        logout_api()
        exit()

def token():
    try:
        login_api = requests.post('%s/api_jsonrpc.php' % zbx_server, headers = {'Content-type': 'application/json'}, verify=False,\
            data = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "user.login",
                    "params": {
                        "user": zbx_user,
                        "password": zbx_pass
                    },
                    "id": 1
                }
            )
        )

        login_api = json.loads(login_api.text.encode('utf-8'))

        if 'result' in login_api:
            auth = login_api["result"]
            return auth

        elif 'error' in login_api:
            print('Zabbix: %s' % login_api["error"]["data"])
            exit()
        else:
            print(login_api)
            exit()

    except ValueError as e:
        print('Check declared zabbix URL/IP and try again | Valide a URL/IP do Zabbix declarada e tente novamente\nCurrent: %s' % zbx_server)
        log.writelog('Check declared zabbix URL/IP and try again | Valide a URL/IP do Zabbix declarada e tente novamente. (Current: {0})'.format(zbx_server), arqLog, "WARNING")
        exit()
    except Exception as e:
        print(e)
        log.writelog('{0}'.format(str(e)), arqLog, "WARNING")
        exit()

def version_api():
    resultado = requests.post('{0}/api_jsonrpc.php'.format(zbx_server), headers = {'Content-type': 'application/json'}, verify=False,\
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "apiinfo.version",
                "params": [],
                "id": 5
            }
        )
    )
    resultado = json.loads(resultado.content.encode('utf-8'))
    if 'result' in resultado:
        resultado = resultado["result"]
    return resultado

def logout_api():
    #import ipdb; ipdb.set_trace()
    logout = requests.post('%s/api_jsonrpc.php' % zbx_server, headers = {'Content-type': 'application/json'}, verify=False,\
        data = json.dumps(
            {
                "jsonrpc": "2.0",
                "method": "user.logout",
                "params": [],
                "auth": auth,
                "id": 4
            }
        )
    )

def getgraph():
    stime = int(PropertiesReaderX(path.format('configScrips.properties')).getValue('PathSection', 'stime'))  # Graph start time [3600 = 1 hour ago]  |  Hora inicial do grafico [3600 = 1 hora atras]
    try:
        loginpage = requests.get('%s/index.php' % zbx_server, auth=(zbx_user, zbx_pass), verify=False).text
        enter = re.search('<button.*value=".*>(.*?)</button>', loginpage)
        s = requests.Session()

        try:
            enter = str(enter.group(1))
            s.post('%s/index.php?login=1' % zbx_server, params={'name': zbx_user, 'password': zbx_pass, 'enter': enter}, verify=False).text
        except:
           pass

        stime = time.strftime("%Y%m%d%H%M%S", time.localtime(time.time() - stime))

        get_graph = s.get('%s/chart3.php?name=%s&period=%s&width=%s&height=%s&stime=%s&items[0][itemid]=%s&items[0][drawtype]=5&items[0][color]=%s' % (zbx_server, itemname, period, width, height, stime, itemid, color))

        sid = s.cookies.items()[0][1]
        s.post('{0}/index.php?reconnect=1&sid={1}'.format(zbx_server, sid))

        return get_graph

    except BaseException:
        log.writelog(
            'Can\'t connect to {0}/index.php | Não foi possível conectar-se à {0}/index.php'.format(zbx_server), arqLog,
            "CRITICAL")
        logout_api()
        exit()

def getItemType():
    try:
        limit = 1000
        itemid = requests.post('%s/api_jsonrpc.php' % zbx_server, headers = {'Content-type': 'application/json'}, verify=False,\
            data = json.dumps(
                {
                    "jsonrpc": "2.0",
                    "method": "item.get",
                    "params": {
                        "output": ["itemid", "name", "lastvalue", "value_type"],
                        "limit": limit,
                        "sortfield": "itemid",
                        "sortorder": "DESC"
                    },
                    "auth": auth,
                    "id": 3
                }
            )
        )

        ValuesItemid = ()
        ValueItemid = json.loads(itemid.content)
        if 'result' in ValueItemid:
            resultado = ValueItemid["result"]
            for i in range(0, len(resultado)):
                if resultado[i]['lastvalue'] != '0' and re.search("(0|3)", resultado[i]['value_type']):
                    if resultado[i]['lastvalue']:
                        ValuesItemid += (resultado[i]['itemid'], resultado[i][u'name'], resultado[i]['value_type'])
                        break

        # itemid = json.loads(itemid.text.encode('utf-8'))['result'][0]['itemid']
        return ValuesItemid

    except Exception as msg:
        print(msg)

def main():
    global subject, body, itemid, itemname, period, color
    try:
        try:
            itemid, itemname, item_type = getItemType()
        except:
            print(
                'User has no read permission on environment | Usuário sem permissão de leitura no ambiente')
            log.writelog(
                'User has no read permission on environment | Usuário sem permissão de leitura no ambiente',
                arqLog, "WARNING")
            logout_api()
            exit()

        color = '00C800'
        period = 3600
        subject = 'testando o envio com o item:'
        body = "{0}".format(itemname)

        if sys.version_info < (3, 0):
            body = itemname.encode('utf-8')

        if "nograph" in sys.argv:
            item_type = "1"
            get_graph = ""
        else:
            get_graph = getgraph()

        dest = sys.argv[1]
        destino = destinatarios(dest)

        for x in destino:
            if not re.search("^.*@[a-z0-9]+\.[a-z]+(\.[a-z].*)?$", x.lower()):
                telegram = x.replace(" ", "_")
                send_telegram(telegram, item_type, get_graph)

    except Exception as msg:
        print(msg)

if __name__ == '__main__':
    auth = token()
    main()
    logout_api()
