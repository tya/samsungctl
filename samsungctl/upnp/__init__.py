# -*- coding: utf-8 -*-
import requests
from xml.dom.minidom import Document
from xml.etree import cElementTree as ElementTree

SEC_XMLNS = '{http://www.sec.co.kr/dlna}'
DEVICE_XMLNS = '{urn:schemas-upnp-org:device-1-0}'
ENVELOPE_XMLNS = 'http://schemas.xmlsoap.org/soap/envelope/'
SERVICE_XMLNS = '{urn:schemas-upnp-org:service-1-0}'
DLNA_XMLNS = '{urn:schemas-dlna-org:device-1-0}'
PNPX_XMLNS = '{http://schemas.microsoft.com/windows/pnpx/2005/11}'
DF_XMLNS = '{http://schemas.microsoft.com/windows/2008/09/devicefoundation}'


def response_xmlns(service, tag):
    return '{' + service + '}' + tag


def envelope_xmlns(tag):
    return '{' + ENVELOPE_XMLNS + '}' + tag


def service_xmlns(tag):
    return SERVICE_XMLNS + tag


def sec_xmlns(tag):
    return SEC_XMLNS + tag


def device_xmlns(tag):
    return DEVICE_XMLNS + tag


def dlna_xmlns(tag):
    return DLNA_XMLNS + tag


def pnpx_xmlns(tag):
    return PNPX_XMLNS + tag


def df_xmlns(tag):
    return DF_XMLNS + tag


class Icon(object):

    def __init__(self, url, node):
        self.mime_type = None
        self.width = None
        self.height = None
        self.depth = None
        self.url = None

        for item in node:
            tag = item.tag.replace(DEVICE_XMLNS, '')
            try:
                text = int(item.text)
            except ValueError:
                text = item.text
            if tag == 'url':
                name = text.split('\\')[-1].replace('.', '_')
                self.__name__ = name[0].upper() + name[1:]
                text = url + text.encode('utf-8')

            setattr(self, tag, text)

    @property
    def data(self):
        return requests.get(self.url).content


class Service(object):

    def __init__(self, url, location, service, control_url):
        self.variables = {}
        self.methods = {}

        response = requests.get(url + location)
        root = ElementTree.fromstring(response.content)

        methods = root.find(service_xmlns('actionList')) or []
        variables = root.find(service_xmlns('serviceStateTable')) or []
        for variable in variables:
            variable = Variable(variable)
            self.variables[variable.__name__] = variable

        for method in methods:
            method = Method(
                method,
                self.variables,
                service,
                url + control_url.encode('utf-8')
            )
            self.methods[method.__name__] = method

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if item in self.methods:
            return self.methods[item]

        raise AttributeError(item)

    def __str__(self):
        output = ''
        for method in self.methods.values():
            output += str(method) + '\n'

        return output


class Method(object):

    def __init__(self, node, variables, service, control_url):
        self.params = []
        self.ret_vals = []
        self.service = service
        self.control_url = control_url

        self.__name__ = node.find(service_xmlns('name')).text
        arguments = node.find(service_xmlns('argumentList')) or []

        for argument in arguments:
            name = argument.find(service_xmlns('name')).text
            direction = argument.find(service_xmlns('direction')).text
            variable = argument.find(service_xmlns('relatedStateVariable')).text
            variable = variables[variable]

            if direction == 'in':
                self.params += [dict(name=name, variable=variable)]
            else:
                self.ret_vals += [dict(name=name, variable=variable)]

    def __call__(self, *args, **kwargs):
        for i, arg in enumerate(args):
            try:
                kwargs[self.params[i]['name']] = arg
            except IndexError:
                for param in self.params:
                    print(param['name'])

                raise

        doc = Document()

        envelope = doc.createElementNS('', 's:Envelope')
        envelope.setAttribute(
            'xmlns:s',
            ENVELOPE_XMLNS
        )
        envelope.setAttribute(
            's:encodingStyle',
            'http://schemas.xmlsoap.org/soap/encoding/'
        )

        body = doc.createElementNS('', 's:Body')

        fn = doc.createElementNS('', self.__name__)
        fn.setAttribute('xmlns:u', self.service)

        for param in self.params:
            if param['name'] not in kwargs:
                value = param['variable'](None)
            else:
                value = param['variable'](kwargs[param['name']])

            tmp_node = doc.createElement(param['name'])
            tmp_text_node = doc.createTextNode(str(value))
            tmp_node.appendChild(tmp_text_node)
            fn.appendChild(tmp_node)

        body.appendChild(fn)
        envelope.appendChild(body)
        doc.appendChild(envelope)
        pure_xml = doc.toxml()

        header = {
            'SOAPAction':   '"{service}#{method}"'.format(
                service=self.service,
                method=self.__name__
            ),
            'Content-Type': 'text/xml'
        }

        response = requests.post(
            self.control_url,
            data=pure_xml,
            headers=header
        )

        envelope = ElementTree.fromstring(response.content)
        body = envelope.find(envelope_xmlns('Body'))

        return_value = []

        if body is not None:

            response = body.find(
                response_xmlns(self.service, self.__name__ + 'Response')
            )
            if response is not None:
                for ret_val in self.ret_vals:
                    value = response.find(ret_val['name'])
                    if value is None:
                        value = ret_val['variable'].convert(None)
                    else:
                        value = ret_val['variable'].convert(value.text)

                    return_value += [value]

        if not return_value and self.ret_vals:
            for val in self.ret_vals:
                value = val['variable'].convert(None)
                return_value += [value]

        return return_value

    def __str__(self):
        output = [
            '',
            'Method Name: ' + self.__name__,
            '  Parameters:'
        ]
        for param in self.params:
            output += [
                '    ' + param['name']
            ]
            param['variable'].direction = 'in'
            variable = str(param['variable']).split('\n')
            variable = list('    ' + line for line in variable)
            output += variable

        output += [
            '  Return Values:'
        ]
        for val in self.ret_vals:

            output += [
                '    ' + val['name']
            ]

            val['variable'].direction = 'out'

            variable = str(val['variable']).split('\n')
            variable = list('    ' + line for line in variable)
            output += variable

        return '\n'.join(output)


class Variable(object):

    def __init__(self, node):
        self.minimum = None
        self.maximum = None
        self.step = None
        self.allowed_values = None
        self.default_value = None
        self.direction = 'in'

        self.__name__ = node.find(service_xmlns('name')).text

        data_type = node.find(service_xmlns('dataType')).text
        if data_type.startswith('ui') or data_type.startswith('i'):
            data_type = int
            allowed = node.find(service_xmlns('allowedValueRange'))
            if allowed is not None:
                minimum = allowed.find(service_xmlns('minimum'))
                maximum = allowed.find(service_xmlns('maximum'))
                step = allowed.find(service_xmlns('step'))

                if minimum is not None:
                    self.minimum = int(minimum.text)
                if maximum is not None:
                    self.maximum = int(maximum.text)
                if step is not None:
                    self.step = int(step.text)

        elif data_type == 'string':
            data_type = str
            allowed = node.find(service_xmlns('allowedValueList'))
            if allowed is not None:
                self.allowed_values = list(value.text for value in allowed)

        elif data_type == 'boolean':
            data_type = bool

        else:
            raise RuntimeError(data_type)

        default_value = node.find(service_xmlns('defaultValue'))
        if default_value is not None:
            if default_value.text == 'NOT_IMPLEMENTED':
                self.default_value = 'NOT_IMPLEMENTED'
            else:
                self.default_value = data_type(default_value.text)

        self.data_type = data_type

    def __call__(self, value):
        if not isinstance(value, self.data_type):
            raise TypeError('Incorrect data type')

        if value is None:
            if self.default_value is None:
                raise ValueError('A value must be supplied')
            if self.default_value == 'NOT_IMPLEMENTED':
                raise ValueError('Not Implemented')
            value = self.default_value

        if self.data_type == int:
            if self.minimum is not None and value < self.minimum:
                raise ValueError(
                    'Value {0} is lower then the minimum of {1}'.format(
                        value,
                        self.minimum
                    )
                )

            if self.maximum is not None and value > self.maximum:
                raise ValueError(
                    'Value {0} is higher then the maximum of {1}'.format(
                        value,
                        self.maximum
                    )
                )

        elif self.data_type == str:
            if (
                self.allowed_values is not None and
                value not in self.allowed_values
            ):
                raise ValueError(
                    'Value {0} not allowed. allowed values are \n{1}'.format(
                        value,
                        self.allowed_values
                    )
                )

        elif self.data_type == bool:
            if value not in (0, 1, True, False):
                raise ValueError(
                    'Boolean value only allowed (0, 1, True, False)'
                )
            value = bool(value)

        return value

    def convert(self, value):
        if not value:
            if self.default_value is not None:
                return self.default_value
        else:
            if self.data_type == bool:
                if value == 'Yes':
                    return True
                if value == 'No':
                    return False
                if value.isdigit():
                    return bool(int(value))
                return bool(value)

            try:
                return self.data_type(value)
            except ValueError:
                return value

    def __str__(self):
        output = [
            '    Data Type Name: ' + self.__name__,
            '    Data Type: ' + str(self.data_type)
        ]

        if self.default_value is not None:
            output += [
                '    Default: ' + repr(self.default_value)
            ]
        if self.minimum is not None:
            output += [
                '    Minimum: ' + str(self.minimum)
            ]
        if self.maximum is not None:
            output += [
                '    Maximum: ' + str(self.maximum)
            ]
        if self.step is not None:
            output += [
                '    Step: ' + str(self.step)
            ]
        if self.allowed_values is not None:

            if self.direction == 'in':
                output += ['    Allowed values:']
            else:
                output += ['    Possible returned values:']
            for item in self.allowed_values:
                output += ['        ' + repr(item)]

        return '\n'.join(output) + '\n'


class UPNPControlBase(object):

    def __init__(self, url, location):
        response = requests.get(url + location)
        root = ElementTree.fromstring(response.content)

        device = root.find(device_xmlns('device'))
        icons = device.find(device_xmlns('iconList')) or []
        services = device.find(device_xmlns('serviceList')) or []

        self._device = device

        self.icon_sml_jpg = None
        self.icon_lrg_jpg = None
        self.icon_sml_png = None
        self.icon_lrg_png = None

        for icon in icons:
            icon = Icon(url, icon)
            setattr(self, icon.__name__.lower(), icon)

        for service in services:
            scpdurl = service.find(device_xmlns('SCPDURL')).text
            control_url = service.find(device_xmlns('controlURL')).text
            service_id = service.find(device_xmlns('serviceId')).text
            service_type = service.find(device_xmlns('serviceType')).text
            scpdurl = b'/' + location[1:].split(b'/')[0] + b'/' + scpdurl.encode('utf-8')

            service = Service(url, scpdurl, service_type, control_url)
            name = service_id.split(':')[-1]
            service.__name__ = name
            attr_name = ''
            last_char = ''

            for char in list(name):
                if char.isdigit():
                    continue

                if char.isupper():
                    if attr_name and not last_char.isupper():
                        attr_name += '_'

                if last_char.isupper():
                    last_char = ''
                else:
                    last_char = char
                attr_name += char.lower()

            setattr(self, attr_name, service)

    def _get_xml_text(self, tag):
        value = self._device.find(device_xmlns(tag))
        if value is not None:
            value = value.text

        return value

    @property
    def device_type(self):
        return self._get_xml_text('deviceType')

    @property
    def friendly_name(self):
        return self._get_xml_text('friendlyName')

    @property
    def manufacturer(self):
        return self._get_xml_text('manufacturer')

    @property
    def manufacturer_url(self):
        return self._get_xml_text('manufacturerURL')

    @property
    def model_description(self):
        return self._get_xml_text('modelDescription')

    @property
    def model_name(self):
        return self._get_xml_text('modelName')

    @property
    def model_number(self):
        return self._get_xml_text('modelNumber')

    @property
    def model_url(self):
        return self._get_xml_text('modelURL')

    @property
    def serial_number(self):
        return self._get_xml_text('serialNumber')

    @property
    def udn(self):
        return self._get_xml_text('UDN')

    @property
    def upc(self):
        return self._get_xml_text('UPC')

    @property
    def device_id(self):
        value = self._device.find(sec_xmlns('deviceID'))
        if value is not None:
            value = value.text

        return value

    @property
    def x_compatible_id(self):
        value = self._device.find(pnpx_xmlns('X_compatibleId'))
        if value is not None:
            value = value.text

        return value

    @property
    def x_device_category(self):
        value = self._device.find(df_xmlns('X_deviceCategory'))
        if value is not None:
            value = value.text

        return value

    @property
    def x_dlnadoc(self):
        value = self._device.find(dlna_xmlns('X_DLNADOC'))
        if value is not None:
            value = value.text

        return value


from samsungctl.upnp.media_renderer import MediaRenderer # NOQA
from samsungctl.upnp.main_tv_server import MainTVServer # NOQA
from samsungctl.upnp.remote_receiver import RemoteReceiver # NOQA
from samsungctl.remote_legacy import RemoteLegacy
from samsungctl.remote_websocket import RemoteWebsocket


class UPNPTV(object):

    def __init__(
        self,
        ip,
        main_tv_server_loc,
        media_renderer_loc,
        remote_receiver_loc
    ):
        self.ip_address = ip
        url_template = b'http://'

        url = url_template + (
            main_tv_server_loc.replace(b'http://', b'').split(b'/')[0]
        )
        main_tv_server_loc = main_tv_server_loc.replace(url, b'')
        media_renderer_loc = media_renderer_loc.replace(url, b'')
        remote_receiver_loc = remote_receiver_loc.replace(url, b'')

        self.main_tv_server = MainTVServer(url, main_tv_server_loc)
        self.media_renderer = MediaRenderer(url, media_renderer_loc)
        self.remote_receiver = RemoteReceiver(url, remote_receiver_loc)

        url = 'http://{0}:8001/api/v2'.format(ip)

        try:
            response = requests.get(url)
            response = response.json()
            if 'device' in response:
                self._tv_options = response['device']
            else:
                self._tv_options = {}
        except:
            self._tv_options = {}

        if self.year <= 2014:
            self.remote = RemoteLegacy(ip, self.device_id)
        else:
            self.remote = RemoteWebsocket(ip, self.device_id)

    def __str__(self):
        output = 'IP Address: ' + self.ip_address + '\n' + '-' * 40 + '\n\n'
        output += str(self.main_tv_server) + '\n'
        output += str(self.media_renderer) + '\n'
        output += str(self.remote_receiver) + '\n'
        return output

    def __enter__(self):
        return self.remote

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        self.remote.close()

    @property
    def operating_system(self):
        if 'OS' in self._tv_options:
            return self._tv_options['OS']
        return 'Unknown'

    @property
    def frame_tv_support(self):
        if 'FrameTVSupport' in self._tv_options:
            return self._tv_options['FrameTVSupport']
        return 'Unknown'

    @property
    def game_pad_support(self):
        if 'GamePadSupport' in self._tv_options:
            return self._tv_options['GamePadSupport']
        return 'Unknown'

    @property
    def voice_support(self):
        if 'VoiceSupport' in self._tv_options:
            return self._tv_options['VoiceSupport']
        return 'Unknown'

    @property
    def firmware_version(self):
        if 'firmwareVersion' in self._tv_options:
            return self._tv_options['firmwareVersion']

        return 'Unknown'

    @property
    def network_type(self):
        if 'networkType' in self._tv_options:
            return self._tv_options['networkType']
        return 'Unknown'

    @property
    def resolution(self):
        if 'resolution' in self._tv_options:
            return self._tv_options['resolution']
        return 'Unknown'

    @property
    def wifi_mac(self):
        if 'wifiMac' in self._tv_options:
            return self._tv_options['wifiMac']
        return 'Unknown'

    @property
    def device_id(self):
        return self.main_tv_server.device_id

    @property
    def panel_technology(self):
        technology_mapping = dict(
            Q='QLED',
            U='LED',
            P='Plasma',
            L='LCD',
            H='DLP',
            K='OLED',
        )

        try:
            return technology_mapping[self.model[0]]
        except KeyError:
            return 'Unknown'

    @property
    def panel_type(self):
        model = self.model
        if model[0] == 'Q' and model[4] == 'Q':
            return 'UHD'
        if model[5].isdigit():
            return 'FullHD'

        panel_mapping = dict(
            S='Slim' if self.year == 2012 else 'SUHD',
            U='UHD',
            P='Plasma',
            H='Hybrid',
        )

        return panel_mapping[model[5]]

    @property
    def size(self):
        return int(self.model[2:][:2])

    @property
    def model(self):
        return self.main_tv_server.model_name

    @property
    def brightness(self):
        return self.media_renderer.brightness

    @brightness.setter
    def brightness(self, value):
        self.media_renderer.brightness = value

    @property
    def contrast(self):
        return self.media_renderer.contrast

    @contrast.setter
    def contrast(self, value):
        self.media_renderer.contrast = value

    @property
    def sharpness(self):
        return self.media_renderer.sharpness

    @sharpness.setter
    def sharpness(self, value):
        self.media_renderer.sharpness = value

    @property
    def color_temperature(self):
        return self.media_renderer.color_temperature

    @color_temperature.setter
    def color_temperature(self, value):
        self.media_renderer.color_temperature = value

    @property
    def position_info(self):
        return self.media_renderer.position_info

    @property
    def channel_list(self):
        return self.main_tv_server.channel_list

    @property
    def source_list(self):
        return self.main_tv_server.source_list

    @property
    def source(self):
        return self.main_tv_server.source

    @source.setter
    def source(self, value):
        self.main_tv_server.source = value

    @property
    def channel(self):
        return self.main_tv_server.channel

    @channel.setter
    def channel(self, value):
        self.main_tv_server.channel = value

    @property
    def mute(self):
        return self.main_tv_server.mute

    @mute.setter
    def mute(self, value):
        self.main_tv_server.mute = value

    @property
    def volume(self):
        return self.main_tv_server.volume

    @volume.setter
    def volume(self, value):
        self.main_tv_server.volume = value

    @property
    def watching_information(self):
        return self.main_tv_server.watching_information

    @property
    def year(self):
        dtv_information = self.main_tv_server.dtv_information
        year = dtv_information.find('SupportTVVersion')
        return int(year.text)

    @property
    def region(self):
        dtv_information = self.main_tv_server.dtv_information
        location = dtv_information.find('TargetLocation')
        return location.text.replace('TARGET_LOCATION_', '')

    @property
    def tuner_count(self):
        dtv_information = self.main_tv_server.dtv_information
        tuner_count = dtv_information.find('TunerCount')
        return int(tuner_count.text)

    @property
    def dtv_support(self):
        dtv_information = self.main_tv_server.dtv_information
        dtv = dtv_information.find('SupportDTV')
        return True if dtv.text == 'Yes' else False

    @property
    def pvr_support(self):
        dtv_information = self.main_tv_server.dtv_information
        pvr = dtv_information.find('SupportPVR')
        return True if pvr.text == 'Yes' else False

    def run_browser(self, url):
        self.main_tv_server.run_browser(url)

    def source_label(self, source, label):
        self.main_tv_server.edit_source_name(source, label)


from samsungctl.upnp.discover import discover # NOQA

