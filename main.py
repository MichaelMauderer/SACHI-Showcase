from __future__ import print_function
import csv

import math
import os

from libavg import avg, player
from libavg import app
from libavg.utils import getMediaDir

X_RES, Y_RES = 1920, 1080

CENTER_CIRCLE_SIZE = X_RES // 20
PERSON_NODE_SIZE_MEDIUM = X_RES // 95
PERSON_NODE_SIZE_LARGE = PERSON_NODE_SIZE_MEDIUM * 3 // 2
STROKE_COLOR = 'FFFFFF'
STROKE_WIDTH = 4

PEOPLE_DATA_PATH = './media/input_csv_file.csv'
PEOPLE_DATA_FIELDNAMES = ['NAME', 'WEB_LINK', 'IMAGE_PATH', 'IS_BIG', 'POS']


def get_people_data():
    result = []

    with open(PEOPLE_DATA_PATH) as in_file:
        for person_dict in csv.DictReader(in_file,
                                          fieldnames=PEOPLE_DATA_FIELDNAMES):
            result.append(person_dict)

    result.sort(key=lambda x: int(x['POS']))
    return result


def get_circle_coordinates(center, radius, num):
    for n in range(num):
        rad = 2 * math.pi * n / num
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

        if int(data['IS_BIG']) == 1:
            size = PERSON_NODE_SIZE_LARGE
        else:
            size = PERSON_NODE_SIZE_MEDIUM

        self._image = avg.CircleNode(r=size,
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


    def _on_click(self, event):
        self.notifySubscribers(self.PERSON_SELECTED, [self._data])


class SACHIShowcase(app.MainDiv):
    def onInit(self):
        self.mediadir = getMediaDir(__file__)
        self.main_div = avg.DivNode(parent=self)

        bg = avg.ImageNode(href='bg.jpg',
                           parent=self.main_div, size=self.size)

        self.people_div = avg.DivNode(parent=self.main_div)

        self.info_div = avg.DivNode(parent=self.main_div)
        self.info_pane = avg.WordsNode(parent=self.info_div,
                                       pos=(
                                           self.size.x * 3 // 4,
                                           self.size.y // 3),
                                       )

        self.center_node = avg.CircleNode(r=CENTER_CIRCLE_SIZE,
                                          parent=self.people_div,
                                          pos=(
                                              self.size.x // 4,
                                              self.size.y // 2),
                                          color=STROKE_COLOR,
                                          strokewidth=STROKE_WIDTH,
                                          fillcolor='FFFFFF',
                                          fillopacity=1,

                                          )

        people_data = get_people_data()
        for data, coords in zip(people_data,
                                get_circle_coordinates(self.center_node.pos,
                                                       200, len(people_data))):
            avg.LineNode(pos1=coords, pos2=self.center_node.pos,
                         strokewidth=STROKE_WIDTH,
                         parent=self.people_div)

            node = PersonNode(data, parent=self.people_div)
            node.pos = coords
            node.subscribe(node.PERSON_SELECTED, self.on_person_selected)

    def on_person_selected(self, data):
        self.info_pane.text = self.get_person_info(data['WEB_LINK'])

    def on_person_hover(self, event, node):
        r = node.r
        avg.EaseInOutAnim(node, "r", 500, r, 2 * r, 100, 100).start()

    def on_person_hover_out(self, event, node):
        r = node.r
        avg.EaseInOutAnim(node, "r", 500, r, r // 2, 100, 100).start()

    def get_person_info(self, url):
        return url


if __name__ == '__main__':
    app.App().run(SACHIShowcase(), app_resolution=str('1280x720'))