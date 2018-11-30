# -*- coding: utf-8 -*-

from samsungctl.upnp import UPNPControlBase
from xml.sax import saxutils
from xml.etree import cElementTree as ElementTree


class MainTVServer(UPNPControlBase):

    def __init__(self, url, location):
        self.main_tv_agent = None
        UPNPControlBase.__init__(self, url, location)

    def __str__(self):
        output = 'MainTVServer\n' + '=' * 40 + '\ninstance.main_ty_server.main_tv_agent\n'
        output += str(self.main_tv_agent)
        return output

    @property
    def dtv_information(self):
        response, data = self.main_tv_agent.GetDTVInformation()
        data = saxutils.unescape(data)
        return ElementTree.fromstring(data)

    def enforce_ake(self):
        return self.main_tv_agent.EnforceAKE()[0]

    def get_all_program_information_url(self, antenna_mode, channel):
        return self.main_tv_agent.GetAllProgramInformationURL(
            antenna_mode,
            channel
        )[1]

    @property
    def banner_information(self):
        return self.main_tv_agent.GetBannerInformation()[1]

    @property
    def channel_list(self):
        (
            version,
            supported_channels,
            channel_list_url,
            channel_list_type,
            satellite_id,
            sort
        ) = self.main_tv_agent.GetChannelListURL()[1:]

        channels = saxutils.unescape(supported_channels)
        channels = ElementTree.fromstring(channels)

        supported_channels = []

        for channel in channels:
            chnl = {}

            for itm in channel:
                value = itm.text
                if value is not None and value.isdigit():
                    value = int(value)

                tag = ''
                last_char = ''
                for char in list(itm.tag):
                    if char.isupper() and tag:
                        if (
                            tag[-1] != '_' and
                            last_char != '_' and
                            not last_char.isupper()
                        ):
                            tag += '_'
                    tag += char.lower()
                    last_char = char

                chnl[tag] = value

            supported_channels += [chnl]

        return dict(
            version=version,
            supported_channels=supported_channels,
            channel_list_url=channel_list_url,
            channel_list_type=channel_list_type,
            satellite_id=satellite_id,
            sort=sort
        )

    def get_channel_lock_information(self, channel, antenna_mode):
        lock, start_time, end_time = (
            self.main_tv_agent.GetChannelLockInformation(
                channel,
                antenna_mode
            )[1:]
        )

        return dict(lock=lock, start_time=start_time, end_time=end_time)

    def get_detail_program_information(
        self,
        antenna_mode,
        channel,
        start_time
    ):
        return self.main_tv_agent.GetDetailProgramInformation(
            antenna_mode,
            channel,
            start_time
        )[1]

    @property
    def network_information(self):
        return self.main_tv_agent.GetNetworkInformation()[1]

    @property
    def antenna_mode(self):
        raise NotImplementedError

    @antenna_mode.setter
    def antenna_mode(self, value):
        self.main_tv_agent.SetAntennaMode(value)

    @property
    def av_off(self):
        raise NotImplementedError

    @av_off.setter
    def av_off(self, value):
        self.main_tv_agent.SetAVOff(value)

    def set_channel_list_sort(self, channel_list_type, satellite_id, sort):
        return self.main_tv_agent.SetChannelListSort(
            channel_list_type,
            satellite_id,
            sort
        )[0]

    def start_clone_view(self, forced_flag):
        """BannerInformation, CloneViewURL, CloneInfo"""
        banner_info, clone_view_url, clone_info = (
            self.main_tv_agent.StartCloneView(forced_flag)[1:]
        )
        return dict(
            banner_info=banner_info,
            clone_view_url=clone_view_url,
            clone_info=clone_info
        )

    def set_clone_view_channel(self, channel_up_down):
        return self.main_tv_agent.SetCloneViewChannel(channel_up_down)[0]

    def start_second_tv_view(
        self,
        antenna_mode,
        channel_list_type,
        satellite_id,
        channel,
        forced_flag
    ):
        banner_info, second_tv_url = (
            self.main_tv_agent.StartSecondTVView(
                antenna_mode,
                channel_list_type,
                satellite_id,
                channel,
                forced_flag
            )[1:]
        )

        return dict(banner_info=banner_info, second_tv_url=second_tv_url)

    def stop_view(self, view_url):
        return self.main_tv_agent.StopView(view_url)[0]

    def add_schedule(self, reservation_type, remind_info):
        return self.main_tv_agent.AddSchedule(reservation_type, remind_info)[1]

    def delete_schedule(self, uid):
        return self.main_tv_agent.DeleteSchedule(uid)[0]

    def change_schedule(self, reservation_type, remind_info):
        return self.main_tv_agent.ChangeSchedule(
            reservation_type,
            remind_info
        )[0]

    def check_pin(self, pin):
        return self.main_tv_agent.CheckPIN(pin)[0]

    def delete_channel_list(self, antenna_mode, channel_list):
        return self.main_tv_agent.DeleteChannelList(
            antenna_mode,
            channel_list
        )[0]

    def delete_channel_list_pin(self, antenna_mode, channel_list, pin):
        return self.main_tv_agent.DeleteChannelListPIN(
            antenna_mode,
            channel_list,
            pin
        )[0]

    def delete_recorded_item(self, uid):
        return self.main_tv_agent.DeleteRecordedItem(uid)[0]

    @property
    def source_list(self):
        source_list = self.main_tv_agent.GetSourceList()[1]
        source_list = saxutils.unescape(source_list)
        root = ElementTree.fromstring(source_list)

        sources = []

        for src in root:
            if src.tag == 'Source':
                source_name = src.find('SourceType').text
                source_id = int(src.find('ID').text)
                source_editable = src.find('Editable').text == 'Yes'
                sources += [
                    Source(
                        source_id,
                        source_name,
                        self,
                        source_editable
                    )
                ]

        return sources

    @property
    def source(self):
        source_id = self.main_tv_agent.GetCurrentExternalSource()[2]
        for source in self.source_list:
            if source.id == int(source_id):
                return source

    @source.setter
    def source(self, source):
        if isinstance(source, int):
            source_id = source
            for source in self.source_list:
                if source.id == source_id:
                    break
            else:
                raise ValueError('Source id not found ({0})'.format(source_id))

        elif not isinstance(source, Source):
            source_name = source
            for source in self.source_list:
                if source_name in (
                    source.name,
                    source.label,
                    source.device_name
                ):
                    break

            else:
                raise ValueError(
                    'Source name not found ({0})'.format(source_name)
                )

        source.activate()

    def start_ext_source_view(self, source, id):
        forced_flag, banner_info, ext_source_view_url = (
            self.main_tv_agent.StartExtSourceView(source, id)[1:]
        )

        return dict(
            forced_flag=forced_flag,
            banner_info=banner_info,
            ext_source_view_url=ext_source_view_url
        )

    def edit_source_name(self, source, name):
        if isinstance(source, int):
            source_id = source
            for source in self.source_list:
                if source.id == source_id:
                    break
            else:
                raise ValueError('Source id not found ({0})'.format(source_id))

        elif not isinstance(source, Source):
            source_name = source
            for source in self.source_list:
                if source_name in (
                    source.name,
                    source.label,
                    source.device_name
                ):
                    break

            else:
                raise ValueError(
                    'Source name not found ({0})'.format(source_name)
                )

        source.label = name

    def set_channel_lock(
        self,
        antenna_mode,
        channel_list,
        lock,
        pin,
        start_time,
        end_time
    ):
        return self.main_tv_agent.SetChannelLock(
            antenna_mode,
            channel_list,
            lock,
            pin,
            start_time,
            end_time
        )[0]

    def set_channel_pin(
        self,
        antenna_mode,
        channel_list_type,
        pin,
        satellite_id,
        channel
    ):
        return self.main_tv_agent.SetMainTVChannelPIN(
            antenna_mode,
            channel_list_type,
            pin,
            satellite_id,
            channel
        )[0]

    @property
    def channel(self):
        channel = self.main_tv_agent.GetCurrentMainTVChannel()[1]
        channel = saxutils.unescape(channel)
        channel = ElementTree.fromstring(channel)

        def get(tag):
            node = channel.find(tag)
            if node is not None:
                try:
                    return int(node.text)
                except ValueError:
                    return node.text

        channel = dict(
            channel_type=get('ChType'),
            major=get('MajorCh'),
            minor=get('MinorCh'),
            ptc=get('PTC'),
            program_number=get('ProgNum')
        )

        return channel

    @channel.setter
    def channel(self, value):
        """value = antenna_mode, channel_list_type, satellite_id, channel"""
        antenna_mode, channel_list_type, satellite_id, channel = value

        self.main_tv_agent.SetMainTVChannel(
            antenna_mode,
            channel_list_type,
            satellite_id,
            channel
        )

    def modify_channel_name(self, antenna_mode, channel, channel_name):
        return self.main_tv_agent.ModifyChannelName(
            antenna_mode,
            channel,
            channel_name
        )[1]

    def edit_channel_number(
        self,
        antenna_mode,
        source,
        destination,
        forced_flag
    ):
        return self.main_tv_agent.EditChannelNumber(
            antenna_mode,
            source,
            destination,
            forced_flag
        )[0]

    @property
    def program_information_url(self):
        return self.main_tv_agent.GetCurrentProgramInformationURL()[1]

    @property
    def current_time(self):
        return self.main_tv_agent.GetCurrentTime()[1]

    def get_detail_channel_information(self, channel, antenna_mode):
        return self.main_tv_agent.GetDetailChannelInformation(
            channel,
            antenna_mode
        )[1]

    @property
    def record_channel(self):
        return self.main_tv_agent.GetRecordChannel()[1]

    def regional_variant_list(self, antenna_mode, channel):
        return self.main_tv_agent.GetRegionalVariantList(
            antenna_mode,
            channel
        )[1]

    @property
    def schedule_list_url(self):
        return self.main_tv_agent.GetScheduleListURL()[1]

    @property
    def watching_information(self):
        tv_mode, information = self.main_tv_agent.GetWatchingInformation()[1:]
        return dict(tv_mode=tv_mode, information=information)

    def modify_favorite_channel(self, antenna_mode, favorite_ch_list):
        return self.main_tv_agent.ModifyFavoriteChannel(
            antenna_mode,
            favorite_ch_list
        )[0]

    def play_recorded_item(self, uid):
        return self.main_tv_agent.PlayRecordedItem(uid)[0]

    def reorder_satellite_channel(self):
        return self.main_tv_agent.ReorderSatelliteChannel()[0]

    def run_app(self, application_id):
        return self.main_tv_agent.RunApp(application_id)[0]

    def run_browser(self, browser_url):
        return self.main_tv_agent.RunBrowser(browser_url)[0]

    def run_widget(self, widget_title, payload):
        return self.main_tv_agent.RunWidget(widget_title, payload)[0]

    @property
    def mute(self):
        status = self.main_tv_agent.GetMuteStatus()[1]
        if status == 'Disable':
            return False
        else:
            return True

    @mute.setter
    def mute(self, mute):
        if mute:
            mute = 'Enable'
        else:
            mute = 'Disable'
        self.main_tv_agent.SetMute(mute)

    @property
    def volume(self, ):
        return self.main_tv_agent.GetVolume()[1]

    @volume.setter
    def volume(self, volume):
        self.main_tv_agent.SetVolume(volume)

    def set_record_duration(self, channel, record_duration):
        return self.main_tv_agent.SetRecordDuration(
            channel,
            record_duration
        )[0]

    def set_regional_variant(self, antenna_mode, channel):
        return self.main_tv_agent.SetRegionalVariant(
            antenna_mode,
            channel
        )[1]

    def send_room_eq_data(
        self,
        total_count,
        current_count,
        room_eq_id,
        room_eq_data
    ):
        return self.main_tv_agent.SendRoomEQData(
            total_count,
            current_count,
            room_eq_id,
            room_eq_data
        )[0]

    def set_room_eq_test(self, room_eq_id):
        return self.main_tv_agent.SetRoomEQTest(room_eq_id)[0]

    def start_instant_recording(self, channel):
        return self.main_tv_agent.StartInstantRecording(channel)[1]

    def start_iperf_client(self, time, window_size):
        return self.main_tv_agent.StartIperfClient(time, window_size)[0]

    def start_iperf_server(self, time, window_size):
        return self.main_tv_agent.StartIperfServer(time, window_size)[0]

    def stop_iperf(self, ):
        return self.main_tv_agent.StopIperf()[0]

    def stop_record(self, channel):
        return self.main_tv_agent.StopRecord(channel)[0]

    def sync_remote_control_pannel(self, channel):
        return self.main_tv_agent.SyncRemoteControlPannel(channel)[1]


class SourceSingleton(type):
    _sources = {}

    def __call__(cls, id, *args):

        if id not in SourceSingleton._sources:
            SourceSingleton._sources[id] = super(SourceSingleton, cls).__call__(id, *args)

        return SourceSingleton._sources[id]


class Source(object):
    __metaclass__ = SourceSingleton

    def __init__(
        self,
        id,
        name,
        parent,
        editable,
    ):
        self._id = id
        self.__name__ = name
        self._parent = parent
        self._editable = editable

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self.__name__

    @property
    def is_viewable(self):
        source = self.__source
        return source.find('SupportView').text == 'Yes'

    @property
    def is_editable(self):
        return self._editable

    @property
    def __source(self):
        source_list = self._parent.main_tv_agent.GetSourceList()[1]
        source_list = saxutils.unescape(source_list)
        root = ElementTree.fromstring(source_list)

        for src in root:
            if src.tag == 'Source':
                if int(src.find('ID').text) == self.id:
                    return src

    @property
    def is_connected(self):
        source = self.__source

        connected = source.find('Connected')
        if connected is not None:
            if connected.text == 'Yes':
                return True
            if connected.text == 'No':
                return False

    @property
    def label(self):
        if self.is_editable:
            source = self.__source

            label = source.find('EditNameType')
            if not label:
                return self.name

            return label.text
        return self.name

    @label.setter
    def label(self, value):
        if self.is_editable:
            self._parent.main_tv_agent.EditSourceName(self.name, value)

    @property
    def device_name(self):
        source = self.__source
        device_name = source.find('DeviceName')
        if device_name is not None:
            return device_name.text

    @property
    def is_active(self):
        source_list = self._parent.main_tv_agent.GetSourceList()[1]
        source_list = saxutils.unescape(source_list)
        root = ElementTree.fromstring(source_list)
        return int(root.find('ID').text) == self.id

    def activate(self):
        if self.is_connected:
            self._parent.main_tv_agent.SetMainTVSource(
                self.name,
                str(self.id),
                str(self.id)
            )

    def __str__(self):
        return self.label
