import json
import os
import random
import subprocess as sp
import socket

import click


@click.group()
def cli():
    pass


def _lxc_ip(name):
    return sp.check_output([
        'sudo', 'lxc-info', '-n', name, '-iH']).strip()


@click.command()
@click.argument('name')
def ssh(name):
    os.execvp('ssh', ['ssh', name, '-l', os.environ['USER']])


@click.command()
@click.argument('name')
@click.option('--release', default=None)
@click.option('--ip',  default=None)
@click.option('--hostname', default=None, multiple=True)
def up(name, release, ip, hostname):
    try:
        output = sp.check_output(
            ['sudo', 'lxc-info', '-n', name, '-sH'])
    except sp.CalledProcessError:
        user = os.environ['USER']
        packages = ['python', 'python-pip']
        cmd = ['sudo', 'lxc-create', '-t', 'ubuntu', '-n', name, '--',
               '--bindhome', user, '--user', user, '--packages',
               ','.join(packages)]
        if release:
            cmd += ['--release', release]
        sp.call(cmd)
        sp.call([
            'ansible', 'all', '-i', '"localhost,"', '-c', 'local', '-m',
            'lineinfile', '-a',
            'dest=/etc/default/lxc-net regexp="LXC_DHCP_CONFILE"'
            ' line="LXC_DHCP_CONFILE=/etc/dnsmasq.d/lxc"',
            '--become'])

        if not ip:
            while True:
                ip = '10.0.3.{}'.format(random.randint(100, 256))
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    if sock.connect_ex((ip, 22)):
                        break
                finally:
                    sock.close()
        sp.call([
            'ansible', 'all', '-i', '"localhost,"', '-c', 'local', '-m',
            'lineinfile', '-a',
            'dest=/etc/dnsmasq.d/lxc line="dhcp-host={},{}"'.format(name, ip),
            '--become'])
        sp.call(['sudo', 'service', 'lxc-net', 'restart'])

        if not hostname:
            hostname = (name,)
        for _hostname in hostname:
            sp.call([
                'ansible', 'all', '-i', '"localhost,"', '-c', 'local', '-m',
                'lineinfile', '-a', 'dest=/etc/hosts line="{0} {1}"'.format(
                    ip, _hostname),
                '--become'])
    finally:
        sp.call(['sudo', 'lxc-start', '-n', name, '--daemon'])


@click.command()
def ls():
    sp.call(['sudo', 'lxc-ls', '--fancy'])


@click.command()
@click.argument('name')
def halt(name):
    sp.call(['sudo', 'lxc-stop', '-n', name, '--nokill'])


@click.command()
@click.argument('names', nargs=-1)
def destroy(names):
    for name in names:
        sp.call(['sudo', 'lxc-stop', '-n', name, '--nokill'])
        sp.call(['sudo', 'lxc-destroy', '-n', name])
        sp.call(
            ['ssh-keygen', '-f', os.path.expanduser('~/.ssh/known_hosts'),
             '-R', name])
        sp.call([
            'ansible', 'all', '-i', '"localhost,"', '-c', 'local', '-m',
            'lineinfile', '-a', 'dest=/etc/hosts state=absent'
            ' regexp="10.0.3.[0-9]* {}"'.format(name),
            '--become'])


@click.command()
@click.argument('name')
@click.option('--playbook', '-p', type=click.Path(exists=True, dir_okay=False))
def provision(name, playbook):
    sp.call([
        'ansible-playbook', '-l', name, '-i', 'lxcw inventory', playbook])


@click.command()
@click.option('--list', is_flag=True)
@click.option('--host')
def inventory(list, host):
    if host:
        data = {'ansible_ssh_host': _lxc_ip(host)}
    else:
        containers = sp.check_output(['sudo', 'lxc-ls']).splitlines()
        data = {'containers': containers}
    click.echo(json.dumps(data))

cli.add_command(destroy)
cli.add_command(halt)
cli.add_command(ls)
cli.add_command(ssh)
cli.add_command(provision)
cli.add_command(up)
cli.add_command(inventory)