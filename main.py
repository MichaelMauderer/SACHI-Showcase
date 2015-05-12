from __future__ import print_function
import csv

import math
import os
import shelve
from threading import Thread

import lxml.html
import urllib
import cgi

from libavg import avg
from libavg import app
from libavg.utils import getMediaDir

X_RES, Y_RES = 1920, 1080

CENTER_CIRCLE_SIZE = X_RES // 20
PERSON_NODE_SIZE_MEDIUM = X_RES // 80
PERSON_NODE_SIZE_LARGE = PERSON_NODE_SIZE_MEDIUM * 3 // 2
STROKE_COLOR = 'FFFFFF'
STROKE_WIDTH = 4

BASE_PEOPLE_CENTRE_DISTANCE = 300

PEOPLE_DATA_PATH = './media/input_csv_file.csv'
PEOPLE_DATA_FIELDNAMES = ['NAME', 'WEB_URL', 'IMAGE_PATH', 'IS_BIG', 'POS']

player = avg.Player.get()


class WebInfoCollector(object):
    def __init__(self, cache_id='web_cache'):
        self._cache_id = cache_id
        self._cache = shelve.open(self._cache_id)

    def load_data_async(self, url):
        thread = Thread(target=self.load_data,
                        args=(url,))
        thread.start()

    def load_data(self, url):
        connection = urllib.urlopen(url)
        dom = lxml.html.fromstring(connection.read())
        content = dom.xpath("//div[@id='content']/div/div[last()]/p")
        cache = shelve.open(self._cache_id)
        elements = [element.text_content() for element in content]
        elements = [cgi.escape(element) for element in elements if element]
        cache[url] = u'<br/><br/>'.join(elements)

    def get_person_info(self, url):
        cache = shelve.open(self._cache_id)
        return cache.get(url, 'Loading...')


info_collector = WebInfoCollector()


def get_people_data():
    result = []

    with open(PEOPLE_DATA_PATH) as in_file:
        for person_dict in csv.DictReader(in_file,
                                          fieldnames=PEOPLE_DATA_FIELDNAMES):
            info_collector.load_data_async(person_dict['WEB_URL'])
            result.append(person_dict)

    result.sort(key=lambda x: int(x['POS']))
    return result


def get_circle_coordinates(center, base_radius, num):
    for n in range(num):
        rad = 2 * math.pi * n / num
        radius = (0.9 * base_radius) if n % 2 == 0 else (base_radius * 1.2)
        x = math.sin(rad) * radius + center[0]
        y = math.cos(rad) * radius + center[1]
        yield x, y


class PersonNode(avg.DivNode):
    PERSON_SELECTED = avg.Publisher.genMessageID()

    def __init__(self, data, parent=None, **kwargs):
        super(PersonNode, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self.publish(self.PERSON_SELECTED)

        self._data = data

        self._resisze_anim = None

        if int(data['IS_BIG']) == 1:
            self._base_size = PERSON_NODE_SIZE_LARGE
        else:
            self._base_size = PERSON_NODE_SIZE_MEDIUM

        self._image = avg.CircleNode(r=self._base_size,
                                     parent=self,
                                     filltexhref=unicode(
                                         os.path.join(
                                             getMediaDir(__file__),
                                             'SACHI_images',
                                             data[
                                                 'IMAGE_PATH'].strip())),
                                     fillopacity=1,
                                     color=STROKE_COLOR,
                                     strokewidth=STROKE_WIDTH,
                                     )

        self._image.subscribe(self._image.CURSOR_DOWN, self._on_click)
        self._image.subscribe(self._image.CURSOR_OVER or self._image.HOVER_OVER,
                              self._on_person_hover)
        self._image.subscribe(self._image.CURSOR_OUT or self._image.HOVER_OUT,
                              self._on_person_hover_out)

    def _abort_resize_anim(self):
        if self._resisze_anim is not None:
            self._resisze_anim.abort()

    def _on_person_hover(self, event):

        self._abort_resize_anim()
        self._resisze_anim = avg.EaseInOutAnim(self._image, "r", 500,
                                               self._image.r,
                                               2 * self._base_size, 100, 100,
                                               )
        self._resisze_anim.start()
        self.notifySubscribers(self.PERSON_SELECTED, [self._data])


    def _on_person_hover_out(self, event):
        self._abort_resize_anim()
        self._resisze_anim = avg.EaseInOutAnim(self._image, "r", 500,
                                               self._image.r, self._base_size,
                                               100, 100)
        self._resisze_anim.start()

    def _on_click(self, event):
        self.notifySubscribers(self.PERSON_SELECTED, [self._data])


class InfoPane(avg.DivNode):
    def __init__(self, parent, **kwargs):
        super(InfoPane, self).__init__(**kwargs)
        self.registerInstance(self, parent)

        self.info_background = avg.RectNode(parent=self,
                                            size=self.size,
                                            fillcolor='000000',
                                            fillopacity=0.3,
                                            strokewidth=0,
                                            )
        words_size = self.info_background.size[0] * 0.8, \
                     self.info_background.size[1] * 0.8
        words_pos = self.info_background.size[0] * 0.1, \
                    self.info_background.size[1] * 0.1
        self.info_pane = avg.WordsNode(parent=self,
                                       pos=words_pos,
                                       size=words_size,
                                       fontsize=15,
                                       alignment="left"
                                       )

        self.heading = avg.WordsNode(parent=self,
                                     pos=(self.size[0] / 2, words_pos[0] / 2),
                                     size=words_size,
                                     fontsize=30,
                                     alignment="center",

                                     )


    def on_person_selected(self, data):
        info_collector.load_data_async(data['WEB_URL'])
        self.info_pane.text = info_collector.get_person_info(data['WEB_URL'])
        self.heading.text = data['NAME']


class SACHIShowcase(app.MainDiv):
    def onInit(self):
        self.mediadir = getMediaDir(__file__)
        self._setup_multitouch()
        self.main_div = avg.DivNode(parent=self)

        # Background Setup
        bg = avg.ImageNode(href='bg.jpg',
                           parent=self.main_div,
                           size=(2 * self.size.x, 2 * self.size.y),
                           pos=(-0.5 * self.size.x, -  0.5 * self.size.y)
                           )
        bg.setEffect(avg.HueSatFXNode(0.0, 40.0, 20.0, False))
        avg.ContinuousAnim(bg, 'angle', 0, 0.1).start()

        bg_particle_overlay = avg.VideoNode(href='particles.avi',
                                            loop=True,
                                            parent=self.main_div,
                                            opacity=0.4,
                                            size=self.size,
                                            fps=15
                                            )
        bg_particle_overlay.play()

        bg_wave_overlay = avg.VideoNode(href='waves.avi',
                                        loop=True,
                                        parent=self.main_div,
                                        opacity=0.4,
                                        size=self.size,
                                        fps=15
                                        )
        bg_wave_overlay.play()

        # Info Pane Setup
        self.info_div = InfoPane(parent=self.main_div,
                                 pos=(
                                     self.size.x * 4 // 7,
                                     self.size.y // 8 ),
                                 size=(self.size.x * 2 // 5,
                                       self.size.y * 6 // 8 ),
                                 )

        # Selection Area Setup
        self.people_canvas = player.createCanvas(id="people",
                                                 size=self.size,
                                                 handleevents=True,
                                                 multisamplesamples=8,
                                                 mipmap=True
                                                 )
        self.people_div = self.people_canvas.getRootNode()
        shaddow = avg.ImageNode(href="canvas:people", parent=self.main_div)
        shaddow.setEffect(avg.ShadowFXNode((0.0, 0.0), 10.0))
        avg.ImageNode(href="canvas:people", parent=self.main_div)

        center_node_pos = (
            self.size.x // 4,
            self.size.y // 2)

        people_data = get_people_data()
        for data, coords in zip(people_data,
                                get_circle_coordinates(center_node_pos,
                                                       BASE_PEOPLE_CENTRE_DISTANCE,
                                                       len(people_data))):
            avg.LineNode(pos1=coords, pos2=center_node_pos,
                         strokewidth=STROKE_WIDTH,
                         parent=self.people_div)

            node = PersonNode(data, parent=self.people_div)
            node.pos = coords
            node.subscribe(node.PERSON_SELECTED,
                           self.info_div.on_person_selected)

        self.center_node_bg = avg.CircleNode(r=CENTER_CIRCLE_SIZE,
                                             parent=self.people_div,
                                             pos=center_node_pos,
                                             color=STROKE_COLOR,
                                             strokewidth=STROKE_WIDTH,
                                             fillcolor='000000',
                                             fillopacity=1,
                                             )

        self.center_node = avg.ImageNode(
            size=(CENTER_CIRCLE_SIZE, CENTER_CIRCLE_SIZE),
            parent=self.people_div,
            pos=(center_node_pos[0] - 0.5 * CENTER_CIRCLE_SIZE,
                 center_node_pos[1] - 0.5 * CENTER_CIRCLE_SIZE),
            href=unicode(
                os.path.join(
                    getMediaDir(__file__),
                    'SACHI_images',
                    'SACHI_logo_whiteTrans.png'))
        )

    def _setup_multitouch(self):
        if app.instance.settings.getBoolean('multitouch_enabled'):
            return

        import platform

        if platform.system() == 'Linux':
            os.putenv('AVG_MULTITOUCH_DRIVER', 'XINPUT')
        elif platform.system() == 'Windows':
            os.putenv('AVG_MULTITOUCH_DRIVER', 'WIN7TOUCH')
        else:
            os.putenv('AVG_MULTITOUCH_DRIVER', 'TUIO')

        try:
            player.enableMultitouch()
        except Exception, e:
            pass


if __name__ == '__main__':
    app.App().run(SACHIShowcase(),
        app_resolution=str('1920x1080'),
        app_fullscreen='true')