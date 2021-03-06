"""
Code ideas from https://github.com/Newmu/dcgan and tensorflow mnist dataset reader
"""
import numpy as np
import random
import cv2
import scipy.misc as misc


class BatchDatset:
    files = []
    images = []
    pad_img = []
    annotations = []
    labels = []
    feature_vector = []
    image_options = {}
    batch_offset = 0
    epochs_completed = 0

    def __init__(self, records_list, image_options={}):
        """
        Intialize a generic file reader with batching for list of files
        :param records_list: list of file records to read -
        sample record: {'image': f, 'annotation': annotation_file, 'filename': filename}
        :param image_options: A dictionary of options for modifying the output image
        Available options:
        resize = True/ False
        resize_size = #size of output image - does bilinear resize
        color=True/False
        """
        print("Initializing Batch Dataset Reader...")
        print(image_options)
        self.files = records_list
        self.image_options = image_options
        self._read_images()

    def _read_images(self):
        self.__channels = True
        self.images = np.array([self._transform(filename['image']) for filename in self.files])
        self.__channels = False
        self.annotations = np.array(
            [np.expand_dims(self._transform(filename['annotation']), axis=3) for filename in self.files])
        # self.annotations = np.array(
        #     [self._transform(filename['annotation']) for filename in self.files])
        print ("image shape:", self.images.shape)
        print ("annotation shape: ", self.annotations.shape)

    def _transform(self, filename):
        image = misc.imread(filename)
        if self.__channels and len(image.shape) < 3:  # make sure images are of shape(h,w,3)
	       image = np.dstack([image, image, image])
            # image = np.array([image for i in range(3)])
	    # print('channel < 3'+str(image.shape))

        if self.image_options.get("resize", False) and self.image_options["resize"]:
            resize_size = int(self.image_options["resize_size"])
            resize_image = misc.imresize(image,
                                         [resize_size, resize_size], interp='nearest')
        else:
            resize_image = image

        return np.array(resize_image)

    def get_records(self):
        return self.images, self.annotations

    def reset_batch_offset(self, offset=0):
        self.batch_offset = offset

    def random_rotate_image(self, img, annotation):
        rotate_flag = random.randint(0,9) % 3
        if (rotate_flag == 0):
            return img, annotation
        else:
            angle = random.randint(1, 3)
            angle *= 90.0
        (h, w) = img.shape[:2]
        rotate_center = (w / 2, h / 2)
        M = cv2.getRotationMatrix2D(rotate_center, angle, scale = 1.0)
        rotated_img = cv2.warpAffine(img, M, (w, h))
        rotated_annotation = cv2.warpAffine(annotation, M, (w, h))
        return rotated_img, np.expand_dims(rotated_annotation, axis = 2)

    def GetFeature(self, _j, _k):
        ret = []
        j = _j + 1
        k = _k + 1
        # height
        ret.append(np.mean(self.pad_img[j, k, :]))
        # x
        ret.append(j)
        # y
        ret.append(k)
        # mean height
        ret.append(np.mean(self.pad_img[j-1:j+2, k-1:k+2, :]))
        # std
        ret.append(np.std(self.pad_img[j-1:j+2, k-1:k+2, :]))
        # min
        ret.append(np.min(self.pad_img[j-1:j+2, k-1:k+2, :]))
        # max
        ret.append(np.max(self.pad_img[j-1:j+2, k-1:k+2, :]))
        # lbp (local binary pattern)
        lbp = 0
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                if (self.pad_img[j+dx, k+dy, 0] >= self.pad_img[j, k, 0]):
                    lbp = lbp * 2 + 1
                else:
                    lbp = lbp * 2
        ret.append(lbp)

        return ret

    def next_batch(self, batch_size, random_rotate):
        start = self.batch_offset
        self.batch_offset += batch_size
        if self.batch_offset > self.images.shape[0]:
            # Finished epoch
            self.epochs_completed += 1
            if (self.epochs_completed % 10 == 0):
                print("****************** Epochs completed: " + str(self.epochs_completed) + "******************")
            # Shuffle the data
            perm = np.arange(self.images.shape[0])
            np.random.shuffle(perm)
            self.images = self.images[perm]
            self.annotations = self.annotations[perm]
            # Start next epoch
            start = 0
            self.batch_offset = batch_size

        end = self.batch_offset
        if (random_rotate):
            for i in range(start, end):
                self.images[i], self.annotations[i] = self.random_rotate_image(self.images[i], self.annotations[i])

        # calculate pixel features
        cnt = 0
        self.feature_vector = []
        self.labels = []
        for i in range(start, end):
            imgSize = self.images[i].shape
            self.pad_img = self.images[i,:,:,:].copy()
            self.pad_img = np.pad(self.pad_img, ((1,1),(1,1),(0,0)), 'edge')
            for j in range(imgSize[0]):
                for k in range(imgSize[1]):
                    if (self.images[i, j, k, 0] > 0):
                        vec = self.GetFeature(j, k)
                        self.feature_vector.append(vec)
                        if self.annotations[i, j, k, 0] == 1:       # green : passable
                            val = 1
                        elif self.annotations[i, j, k, 0] == 2:     # red: unpassable
                            val = -1
                        else:                                       # blue: uncertain
                            val = 1 if random.random() > 0.5 else -1
                        self.labels.append([val])
                        cnt += 1

        return self.feature_vector, self.labels, self.images[start:end]

    def get_random_batch(self, batch_size):
        indexes = np.random.randint(0, self.images.shape[0], size=[batch_size]).tolist()
	fileList = np.array([])
	for i in self.files:
	    fileList = np.append(fileList, i['filename'])
	return self.images[indexes], self.annotations[indexes], fileList[indexes]
