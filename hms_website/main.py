import logging
import subprocess

import coloredlogs

from hms_base.client import Client
from hms_base.decorators import topic

BUILD_COMMAND = "cd /home/oneshot/website-content && git pull && cd /home/oneshot/website && . .venv_pelican/bin/activate && rm -rf cache/ && make publish && deactivate"
RSYNC_COMMAND = "rsync -avc --delete /home/oneshot/website/output/ /var/www/haum.org/build"
INSULTES = ["T'as encore merdé ? Tu fais de la merde là…", "Et c'est le défilé des bugs à la con.", "Quoi ? T'as pété le site ? ... vache... on file des accès à n'importe qui de nos jours.", "Bravo. T'as tout flingué. Continue comme ça, et tu vas te faire claquer par un robot."]



def supercall(command):
    p = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE)
    retval = p.wait()
    
    if retval != 0:
        get_logger().critical('error calling {}'.format(command))
        for line in p.stderr.readlines():
            get_logger().critical(line.decode('utf8').replace('\n', ''))

    return retval


def get_logger():
    return logging.getLogger(__name__)

def updatesite():
    # On essaye de fabriquer le site, et si ça casse pas on rsync

    get_logger().info('Start updatesite')

    ret = supercall(BUILD_COMMAND)
    if ret != 0:
        get_logger().critical('Error building site')
        return False

    get_logger().info('Build ok, start rsync')

    ret = supercall(RSYNC_COMMAND)
    if ret != 0:
        get_logger().critical('Error rsync site')
        return False

    get_logger().info('Success updatesite')

    return True

def main():
    """Entry point of the program."""

    # Logging
    coloredlogs.install(level='INFO')

    # Connect to Rabbit
    rabbit = Client('hms_website', 'haum', ['irc_command'])

    rabbit.connect()

    def voice_required(f):
        """Decorator that checks if the sender is voiced."""
        def wrapper(*args):
            print(args)
            if 'is_voiced' in args[2] and args[2]['is_voiced']:
                return f(*args)
            else:
                rabbit.publish('irc_debug', {'privmsg': 'On se connait ? Tu n’es pas voiced mon ami...'})
        return wrapper


    @topic('irc_command')
    @voice_required
    def callback(client, topic, message):
        if 'command' in message and message['command'] == 'updatesite2':

            rabbit.publish('irc_debug', {'privmsg': 'Mise à jour du site en cours…'})

            success = updatesite()
            message = "T'as tout cassé"

            if success:
                message = "Le site est à jour !"

            rabbit.publish('irc_debug', {'privmsg': message})


    rabbit.listeners.append(callback)
    
    # Infinite listenning for messages
    rabbit.start_consuming()

    rabbit.disconnect()


if __name__ == '__main__':
    main()
