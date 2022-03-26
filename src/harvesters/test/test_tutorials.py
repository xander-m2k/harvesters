#!/usr/bin/env python3
# ----------------------------------------------------------------------------
#
# Copyright 2018 EMVA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ----------------------------------------------------------------------------


# Standard library imports
from logging import Logger
from threading import Thread
import time
from typing import List
import unittest

# Related third party imports
from harvesters.core import Harvester
from harvesters.core import ImageAcquirer

# Local application/library specific imports
from harvesters.test.base_harvester import TestHarvester
from harvesters.test.base_harvester import get_cti_file_path


class AcquisitionThread(Thread):
    def __init__(self, acquire, nr, logger, sleep=0.001):
        super().__init__()
        self._acquire = acquire
        self._nr = nr
        self._sleep = sleep
        self._logger = logger

    def run(self):
        self._acquire.start()
        nr = 0
        while nr < self._nr:
            with self._acquire.fetch() as buffer:
                self._logger.info(
                    'fetched: #{}, buffer: {}, acquire: {}'.format(
                        nr, buffer, self._acquire))
                nr += 1
                time.sleep(self._sleep)
        self._acquire.stop()
        self._acquire.destroy()


class NodeCallbackDemoThread(Thread):
    def __init__(self, acquire, index, logger):
        super().__init__()
        self._acquire = acquire
        self._logger = logger
        self._index = index

    def run(self):
        self._logger.info("{}; GIVEN: an image acquirer".format(self._index))
        self._logger.info("{}; AND GIVEN: an equipped node map".format(self._index))
        self._acquire.remote_device.node_map.Width.value = 100 * (self._index + 1)
        self._acquire.remote_device.node_map.Height.value = 100 * (self._index + 1)
        self._acquire.remote_device.node_map.AcquisitionFrameRate.value = 200

        self._logger.info("{}; WHEN: enabling a node callback".format(self._index))
        context = LoggerIndexPair(logger=self._logger, index=self._index)
        worker = CallbackWorker()
        token = self._acquire.remote_device.register_node_callback(
            node_name='EventGameProgressMessage',
            callback=worker.callback, context=context)

        self._logger.info("{}; THEN: game progress appear".format(self._index))
        self._acquire.start()
        time.sleep(3)
        self._acquire.stop()

        self._logger.info("{}; AND WHEN: disabling a node callback".format(self._index))
        self._acquire.remote_device.deregister_node_callback(token)

        self._logger.info("{}; THEN: game progress does not appear anymore".format(self._index))
        self._acquire.start()
        time.sleep(3)
        self._acquire.stop()

        self._acquire.destroy()


class LoggerIndexPair:
    def __init__(self, *, logger: Logger, index: int = 0):
        self._logger = logger
        self._index = index

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def index(self) -> int:
        return self._index


class CallbackWorker:
    @staticmethod
    def callback(node, context: LoggerIndexPair):
        context.logger.info(
            "source: {}; event: {}".format(context.index, node.value))


class TestTutorials(TestHarvester):

    def test_module_events_on_multiple_devices(self):
        if not self.is_running_with('viky'):
            self.skipTest("the given target is not appropriate")

        threads = []
        nr_devices = len(self.harvester.device_info_list)
        for i in range(nr_devices):
            threads.append(
                NodeCallbackDemoThread(
                    self.harvester.create(i), i, self._logger))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self._logger.info("completed")

    def test_module_events(self):
        if not self.is_running_with('viky'):
            self.skipTest("the given target is not appropriate")

        self._logger.info("SCENARIO: enabling/disabling node callback")

        self._logger.info("GIVEN: an image acquirer")
        ia = self.harvester.create()  # type: ImageAcquirer

        self._logger.info("AND GIVEN: an equipped node map")
        ia.remote_device.node_map.Width.value = 100
        ia.remote_device.node_map.AcquisitionFrameRate.value = 200

        self._logger.info("WHEN: enabling a node callback")
        context = LoggerIndexPair(logger=self._logger)
        worker = CallbackWorker()
        token = ia.remote_device.register_node_callback(
            node_name='EventGameProgressMessage',
            callback=worker.callback, context=context)

        self._logger.info("THEN: game progress appear")
        ia.start()
        time.sleep(3)
        ia.stop()

        self._logger.info("AND WHEN: disabling a node callback")
        ia.remote_device.deregister_node_callback(token)

        self._logger.info("THEN: game progress does not appear anymore")
        ia.start()
        time.sleep(3)
        ia.stop()

        ia.destroy()

    def test_free_running(self):
        # Connect to the first camera in the list.
        self.ia = self.harvester.create_image_acquirer(0)

        #
        num_images_to_acquire = 0

        # Then start image acquisition.
        self.ia.start()

        while num_images_to_acquire < 10:
            #
            with self.ia.fetch() as buffer:
                #
                self._logger.info('{0}'.format(buffer))
            num_images_to_acquire += 1

    def test_severis_usage(self):
        if not self.is_running_with():
            return

        # Connect to the first camera in the list.
        self.ia = self.harvester.create_image_acquirer(0)

        #
        num_images_to_acquire = 0

        # Setup the camera before starting image acquisition.
        self.setup_camera()

        # Then start image acquisition.
        self.ia.start()

        # Setup your equipment then trigger the camera.
        self.setup_equipment_and_trigger_camera()

        while num_images_to_acquire < 10:
            #
            with self.ia.fetch() as buffer:
                #
                self._logger.info('{0}'.format(buffer))

                # TODO: Work with the image you got.
                # self.do_something(buffer)

                # Set up your equipment for the next image acquisition.
                self.setup_equipment_and_trigger_camera()

            num_images_to_acquire += 1

    def setup_camera(self):
        self.ia.remote_device.node_map.AcquisitionMode.value = 'Continuous'
        self.ia.remote_device.node_map.TriggerMode.value = 'On'
        self.ia.remote_device.node_map.TriggerSource.value = 'Software'

    def setup_equipment_and_trigger_camera(self):
        # Setup your equipment.
        # TODO: Code here.

        # Trigger the camera because you have already setup your
        # equipment for the upcoming image acquisition.
        self.ia.remote_device.node_map.TriggerSoftware.execute()

    def test_threading(self):
        if not self.is_running_with():
            return

        threads = []
        nr_devices = len(self.harvester.device_info_list)
        for i in range(nr_devices):
            threads.append(
                AcquisitionThread(
                    self.harvester.create_image_acquirer(i), 10, self._logger))

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        self._logger.info("completed")


class TestTutorials2(unittest.TestCase):
    def setUp(self) -> None:
        # The following block is just for administrative purpose;
        # you should not include it in your code:
        self._cti_file_path = get_cti_file_path()
        if 'TLSimu.cti' not in self._cti_file_path:
            self.skipTest('The target is not TLSimu.')

        # Create a Harvester object:
        self.harvester = Harvester()

    def tearDown(self) -> None:
        #
        self.harvester.reset()

    def is_running_with_default_target(self):
        return True if 'TLSimu.cti' in self._cti_file_path else False

    def test_traversable_tutorial(self):
        # Add a CTI file path:
        self.harvester.add_file(self._cti_file_path)
        self.harvester.update()

        # Connect to the first camera in the list:
        ia = self.harvester.create_image_acquirer(0)

        #
        num_images_to_acquire = 0

        # Then start image acquisition:
        ia.start()

        while num_images_to_acquire < 10:
            #
            with ia.fetch() as buffer:
                # self.do_something(buffer)
                pass

            num_images_to_acquire += 1

        # It's done; stop the image acquisition:
        ia.stop()

        # We don't need the ImageAcquirer object. Destroy it:
        ia.destroy()


if __name__ == '__main__':
    unittest.main()
