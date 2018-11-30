# -*- coding: utf-8 -*-


from samsungctl.upnp import UPNPControlBase


class RemoteReceiver(UPNPControlBase):

    def __init__(self, url, location):
        self.test_rc_rservice = None
        UPNPControlBase.__init__(self, url, location)
        self.test_rcr_service = self.test_rc_rservice
        del self.test_rc_rservice

    def __str__(self):
        output = 'RemoteReceiver\n' + '=' * 40 + '\ninstance.remote_receiver.test_rcr_service\n'
        output += str(self.test_rcr_service)
        return output


'''
urn:samsung.com:device:RemoteControlReceiver:1
<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:sec="http://www.sec.co.kr/dlna" xmlns:dlna="urn:schemas-dlna-org:device-1-0">
    <specVersion>
        <major>1</major>
        <minor>0</minor>
    </specVersion>
    <device>
        <deviceType>urn:samsung.com:device:RemoteControlReceiver:1</deviceType>
        <friendlyName>[TV]UN55D8000</friendlyName>
        <manufacturer>Samsung Electronics</manufacturer>
        <manufacturerURL>http://www.samsung.com/sec</manufacturerURL>
        <modelDescription>Samsung TV RCR</modelDescription>
        <modelName>UN55D8000</modelName>
        <modelNumber>1.0</modelNumber>
        <modelURL>http://www.samsung.com/sec</modelURL>
        <serialNumber>20090804RCR</serialNumber>
        <UDN>uuid:2007e9e6-2ec1-f097-f2df-944770ea00a3</UDN>
        <sec:deviceID>MTCN4UQJAZBMQ</sec:deviceID>
        <serviceList>
            <service>
                <serviceType>urn:samsung.com:service:TestRCRService:1</serviceType>
                <serviceId>urn:samsung.com:serviceId:TestRCRService</serviceId>
                <controlURL>/RCR/control/TestRCRService</controlURL>
                <eventSubURL>/RCR/event/TestRCRService</eventSubURL>
                <SCPDURL>TestRCRService.xml</SCPDURL>
            </service>
        </serviceList>
    </device>
</root>



<scpd xmlns="urn:schemas-upnp-org:service-1-0">
<specVersion>
    <major>1</major>
    <minor>0</minor>
</specVersion>
<actionList>
    <action>
        <name>AddMessage</name>
        <argumentList>
            <argument>
                <name>MessageID</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_MessageID</relatedStateVariable>
            </argument>
            <argument>
                <name>MessageType</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_MessageType</relatedStateVariable>
            </argument>
            <argument>
                <name>Message</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_Message</relatedStateVariable>
            </argument>
        </argumentList>
    </action>
    <action>
        <name>SendKeyCode</name>
        <argumentList>
            <argument>
                <name>KeyCode</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_KeyCode</relatedStateVariable>
            </argument>
            <argument>
                <name>KeyDescription</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_KeyDescription</relatedStateVariable>
            </argument>
        </argumentList>
    </action>
    <action>
        <name>RemoveMessage</name>
        <argumentList>
            <argument>
                <name>MessageID</name>
                <direction>in</direction>
                <relatedStateVariable>A_ARG_TYPE_MessageID</relatedStateVariable>
            </argument>
        </argumentList>
    </action>
</actionList>
<serviceStateTable>
    <stateVariable sendEvents="no">
        <name>A_ARG_TYPE_KeyCode</name>
        <dataType>ui4</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
        <name>A_ARG_TYPE_KeyDescription</name>
        <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
        <name>A_ARG_TYPE_MessageID</name>
        <dataType>string</dataType>
    </stateVariable>
    <stateVariable sendEvents="no">
        <name>A_ARG_TYPE_MessageType</name>
        <dataType>string</dataType>
        <defaultValue>text/xml; charset=&quot;utf-8&quot;</defaultValue>
    </stateVariable>
    <stateVariable sendEvents="no">
        <name>A_ARG_TYPE_Message</name>
        <dataType>string</dataType>
    </stateVariable>
</serviceStateTable>
</scpd>

'''


