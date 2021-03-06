#!/usr/bin/env python
# coding=utf-8

# Author      :   Xionghui Chen
# Created     :   2017.3.27
# Modified    :   2017.3.27
# Version     :   1.0

import base64
import zbar  
import Image   
import datetime
import qrcode  # 导入模块  
import logging
import tornado.web
import tornado.gen
import os

from config.globalVal import ReturnStruct, AP
from Base import BaseHandler,throw_base_exception
from _exceptions.http_error import ArgumentTypeError,InnerError

class CoderHandler(BaseHandler):
    def __init__(self, *argc, **argkw):
        super(CoderHandler, self).__init__(*argc, **argkw)

    def _file_name_creator(self):
        return str(datetime.datetime.now())

class DecoderHandler(CoderHandler):
    def __init__(self, *argc, **argkw):
        super(DecoderHandler, self).__init__(*argc, **argkw)

    @throw_base_exception
    def post(self):
        """
        picture_base64: pass picture encode as base64
        """
        message_mapping = [
        ]
        result = ReturnStruct()
        logging.info("before get base64,time %s"%(datetime.datetime.now()))
        pic = self.get_argument("picture_base64")
        logging.info("before decode 64")
        if pic == '':
            raise ArgumentTypeError("empty picture_base64")
        try:
            binary_picture = base64.b64decode(pic)
        except TypeError as e:
            raise ArgumentTypeError('error change type : picture_base64')
        logging.info("before decoder %s"%(datetime.datetime.now()))
        try:
            result.data['info'] = self._decoder(binary_picture)
        except Exception as e:
            raise ArgumentTypeError('decode failed: ,message %s'%str(e))
        just_info = '0'
        try:
            just_info = self.get_argument('just_info')
        except Exception as e:
            logging.info("exception is %s"%str(e))
        if just_info == '1':
            self.write(result.data['info'])
        else:
	    self.return_to_client(result)
        self.finish()

    def _decoder(self,binary_picture):
        """ change 2-d barcode to data.

        Args：
            binary_picture: a binary picture which content is 2-d binary picture.
        """
        # create a reader  
        scanner = zbar.ImageScanner()  
        # configure the reader  
        scanner.parse_config('enable')
        # obtain image data  
        path = AP+self.servicename+'/'+'static/decoder/'+self._file_name_creator()
        file = open(path,'wb')
        file.write(binary_picture)
        file.close()
        pil = Image.open(path).convert('L') 
        width, height = pil.size  
        logging.info("w is %s, h is %s"%(width,height))
        result_width= 290
        if width > 290:
            height = int(height/(width/result_width))
            width = result_width
            print str(height)
            print str(width)
            logging.info("before resize w is %s, height is %s"%(width,height))
            pil = pil.resize((width,height),Image.ANTIALIAS)
        logging.info("after resize, w is %s, height is %s"%(width, height))
        raw = pil.tostring()  
        # wrap image data  
        image = zbar.Image(width, height, 'Y800', raw)  
        # scan the image for barcodes  
        scanner.scan(image)  

        # extract results
        result = ''
        for symbol in image:  
            # do something useful with results  
            result = symbol.data  
        # clean up  
        os.remove(path)
        del(image)
        return result

class EncoderHandler(CoderHandler):
    def __init__(self, *argc, **argkw):
        super(EncoderHandler, self).__init__(*argc, **argkw)
    
    @tornado.web.asynchronous
    @tornado.gen.engine
    def post(self):
        """
            information: infomation to encode to 2-D barcode
        """
        logging.info("in there1")
        information = self.get_argument("information")
        user_id = self.get_argument('user_id')
        pro_id = self.get_argument('pro_id')
        result = ReturnStruct()
        try:
            if information == '':
                raise TypeError('information')
        except TypeError as e:
            raise ArgumentTypeError('argument: infomation is empty')
        
        try:
            logging.info("before encoder.")
            binary = self._encoder(information)
            data = {
                'user_id':user_id,
                'pro_id':pro_id,
            }
            res = yield self.file_requester(self.resource_service+'/project/post', data, binary,'.png')
            result.data['key']=res['data']['key']
        except Exception as e:
            raise InnerError(str(e)+"in encoder")


        self.return_to_client(result)
        self.finish()

    def _encoder(self,information):
        """ change information to 2-d barcode.

        Args:
            information

        Returns:
            base64 picture
        """
        qr = qrcode.QRCode(  
            version=1,  
            error_correction=qrcode.constants.ERROR_CORRECT_L,  
            box_size=10,  
            border=4,  
        )  
        qr.add_data(information)
        qr.make(fit=True)  
        path = AP+self.servicename+'/static/encoder/'+self._file_name_creator()
        img = qr.make_image()  
        img.save(path)  
        with open(path, 'rb') as f:  
            content = f.read()
            os.remove(path)
            return content
