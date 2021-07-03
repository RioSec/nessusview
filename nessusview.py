#!/usr/bin/env python3
import html
import socket
import sys
import xml.etree.ElementTree as ET


class Host():

    def __init__(self, ip, fqdn):
            self.ip = ip
            self.fqdn = fqdn
            self.findings = {}

    def add_finding(self, finding):
            """ Adds a new finding to the list or updates the port if it already exists. """
            if self.findings.get(finding.plugin_id):
                    self.findings[finding.plugin_id].ports.extend(finding.ports)
            else:
                    self.findings[finding.plugin_id] = finding


class Finding():

    def __init__(self, plugin_id, name, ports, protocol, severity):
            self.plugin_id = plugin_id
            self.plugin_name = name
            self.ports = list(ports)
            self.protocol = protocol
            self.severity = severity


def create_host(host_properties):
    """ Instantiates a Host object from the HostProperties children """
    ip = None
    fqdn = html.escape('<does not resolve>')
    for child in host_properties.findall('tag'):
            if child.attrib.get('name') == 'host-ip':
                    ip = child.text
            if child.attrib.get('name') == 'host-fqdn':
                    fqdn = child.text
    if ip:
            return Host(ip, fqdn)

# HTML Template
HTML_DOC_START = '<html><head><link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous"><style>.host, .plugin {padding: 1em;} h5 {display:inline; padding-right: 1em;} td {width:33%;}</style></head><body>'
HTML_NAV = '<nav><div class="nav nav-tabs" id="nav-tab"><a class="nav-item nav-link active" id="nav-hosts-tab" data-toggle="tab" href="#nav-hosts">Hosts</a><a class="nav-item nav-link" id="nav-plugins-tab" data-toggle="tab" href="#nav-plugins">Plugins</a></div></nav>'
HTML_HOST_TAB_START = '<div class="tab-content" id="nav-tabContent"><div class="tab-pane fade show active" id="nav-hosts">'
HTML_HOST_BLOCK = '<div class="host"><div class="host-header"><h5>{} | {}</h5></div>'.format
HTML_FINDING_BLOCK_START = '<div class="findings"><table class="table table-sm table-hover"><thead><tr><th>Severity</th><th>ID</th><th>Title</th></tr></thead>'
HTML_FINDING_BLOCK = '<tr><td class="{}">{}</td><td>{}</td><td>{}</td></tr>'.format
HTML_FINDING_BLOCK_END = '</table></div>'
HTML_HOST_BLOCK_END = '</div>'
HTML_HOST_TAB_END = '</div>'
HTML_PLUGIN_TAB_START = '<div class="tab-pane fade" id="nav-plugins">'
HTML_PLUGIN_BLOCK_HEADER = '<div class="plugin"><h5>{} | {} | {}</h5><button type="button" class="btn btn-primary btn-sm" onclick="prtCopy(\'{}\')">PRT</button>'.format
HTML_PLUGIN_BLOCK_START = '<div class="hosts"><table class="table table-sm table-hover"><thead><tr><th>IP</th><th>FQDN</th><th>Ports</th></tr></thead>'
HTML_PLUGIN_BLOCK = '<tr><td>{}</td><td>{}</td><td>{}</td></tr>'.format
HTML_PLUGIN_TAB_END = '</div>'
HTML_DOC_END = '<script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script><script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"></script><script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"></script><script>function prtCopy(elem) {var copyText = document.getElementById(elem);copyText.select();document.execCommand("copy");}</script></body></html>'


if __name__ == '__main__':
    # Terminate if no file
    if len(sys.argv) < 3:
        print(f'\nUsage:\n\n {sys.argv[0]} <nessus_file> <results_file>')
        sys.exit()
    xml = sys.argv[1]
    results_file = sys.argv[2]
    # Parse Host Data
    hosts = []
    for event, elem in ET.iterparse(xml, events=('start', 'end')):
        if event == 'end' and elem.tag == 'ReportHost':
            # Create Host
            host = create_host(elem.find('HostProperties'))
            if host:
                # Create Finding
                findings = elem.findall('ReportItem')
                for item in findings:
                    plugin_id = item.attrib['pluginID']
                    plugin_name = item.attrib['pluginName']
                    plugin_port = [item.attrib['port']]
                    plugin_protocol = item.attrib['protocol']
                    plugin_severity = item.attrib['severity']
                    finding = Finding(plugin_id, plugin_name, plugin_port, plugin_protocol, plugin_severity)
                    host.add_finding(finding)
                hosts.append(host)
            elem.clear()

    # Organize Plugin Data
    # plugins = {
    #       123456: [title, (10.0.0.1, my.local, [80, 443])]
    #}
    plugins = {}
    for host in hosts:
        for plugin_id, finding in host.findings.items():
            if not plugins.get(plugin_id):
                plugins[plugin_id] = [finding.plugin_name, finding.severity, (host.ip, host.fqdn, finding.ports)]
            else:
                plugins[plugin_id].append((host.ip, host.fqdn, finding.ports))
            
    # Generate HTML
    with open(results_file, 'w') as fout:
        SEVERITY = {
            '4': 'Critical',
            '3': 'High',
            '2': 'Medium',
            '1': 'Low',
            '0': 'Info'
        }
        COLOR_CLASS = {
            '4': 'text-danger',
            '3': 'text-warning',
            '2': 'text-info',
            '1': 'text-primary',
            '0': 'text-muted'
        }
        fout.write(HTML_DOC_START)
        fout.write(HTML_NAV)
        # Generate host content
        fout.write(HTML_HOST_TAB_START)
        for host in sorted(hosts, key=lambda item: socket.inet_aton(item.ip)):
            fout.write(HTML_HOST_BLOCK(host.ip, host.fqdn))
            fout.write(HTML_FINDING_BLOCK_START)
            for k,v in sorted(host.findings.items(), key=lambda item: item[1].severity, reverse=True):
                fout.write(HTML_FINDING_BLOCK(COLOR_CLASS[v.severity], SEVERITY[v.severity], k, v.plugin_name))
            fout.write(HTML_FINDING_BLOCK_END)
            fout.write(HTML_HOST_BLOCK_END)
        fout.write(HTML_HOST_TAB_END)
        # Generate plugin content
        fout.write(HTML_PLUGIN_TAB_START)
        for plugin_id, host_list in sorted(plugins.items(), key=lambda item: int(item[0])):
            #import pdb;pdb.set_trace()
            fout.write(HTML_PLUGIN_BLOCK_HEADER(SEVERITY[host_list[1]], plugin_id, host_list[0], 'prt-' + plugin_id) +'\n')
            fout.write(HTML_PLUGIN_BLOCK_START)
            prt_table = f'<input style="opacity:0; width:1px;" type="text" id="prt-{plugin_id}" value="<table><tbody>'
            for host in sorted(host_list[2:], key=lambda item: socket.inet_aton(item[0])):
                fout.write(HTML_PLUGIN_BLOCK(host[0], host[1], ','.join(sorted(host[2], key=lambda x: int(x)))))
                prt_table += f'<tr><td>{host[0]}:{",".join(sorted(host[2], key=lambda x: int(x)))}</td><td>{html.escape(host[1])}</td></tr>'
            fout.write(HTML_FINDING_BLOCK_END)
            prt_table += '</tbody></table>"/>'
            fout.write(prt_table)
            fout.write(HTML_PLUGIN_TAB_END)
            fout.write(HTML_HOST_BLOCK_END)
        fout.write(HTML_HOST_TAB_END)
        fout.write(HTML_DOC_END)
