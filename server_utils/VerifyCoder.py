from PIL import Image, ImageDraw, ImageFont
import uuid
import random
import datetime
import math


class VerifyCoder:
    def __init__(self):
        self.guid = uuid.uuid4()
        self.__genesis_code = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        self.code = ""

    def __gene_verify_code(self, size, sources=None):
        if sources is None or sources.length() == 0:
            sources = self.__genesis_code
        rand = random.Random(datetime.datetime.now().timestamp())
        code = ""
        for i in range(size):
            code = code + rand.choice(sources)
        return code

    def __image_gene(self, w, h, code):
        code_size = len(code)
        img_background = self.__get_rand_color(160, 250)
        img = Image.new("RGB", (w, h), img_background)
        img_draw = ImageDraw.Draw(img)
        self.__envelope_draw(w, h, img_draw, (128, 128, 128), 1)
        self.__random_line(w, h, img_draw, 20)
        self.__random_spot(w, h, img_draw)
        color_shear = self.__get_rand_color(200, 250)
        self.__text_code_draw(w, h, code, img, img_draw, code_size)
        self.__shear_x(w, h, color_shear, img_draw, img)
        return img

    def __random_line(self, w, h, draw, count=20):
        line_color = self.__get_rand_color(160, 200)
        for i in range(count):
            x = random.randint(0, w - 1)
            y = random.randint(0, h - 1)
            xl = random.randint(0, 6) + 1
            yl = random.randint(0, 12) + 1
            draw.line([(x, y), (x + xl + 40, y + yl + 20)], fill=line_color)

    def __random_spot(self, w, h, draw):
        yawp_rate = 0.1
        area = int(yawp_rate * w * h)
        for i in range(area):
            x = random.randint(0, w)
            y = random.randint(0, h)
            rgb = self.__get_rand_rgb()
            draw.point((x, y), fill=rgb)

    def __text_code_draw(self, w, h, code, img, draw, size):
        font = ImageFont.truetype("c:\\Windows\\Fonts\\ALGER.TTF", size=(h - 4))
        for each in range(len(code)):
            angle = math.pi / 4 * random.random() * (1 if random.choice((True, False)) else -1)
            x = int((w / size) * each + (h - 4) / 2)
            y = int(h / 2)
            xt = int(((w - 10) / size) * each + 5)
            yt = int(h - (h / 2 + (h - 4) / 2))
            txt = code[each:each + 1]
            draw.text((xt, yt), txt, font=font, fill=self.__get_rand_color(100, 160))

    @staticmethod
    def __build_matrix(angle, x, y):
        return (math.cos(angle), -math.sin(angle), x - x * math.cos(angle) + y * math.sin(angle), math.sin(angle),
                math.cos(angle), y - x * math.sin(angle) - y * math.cos(angle), 0, 0, 1)

    @staticmethod
    def __envelope_draw(w, h, draw, fillcolor, width):
        draw.line([(0, 0), (w - 1, 0)], fill=fillcolor, width=width)
        draw.line([(w - 1, 0), (w - 1, h - 1)], fill=fillcolor, width=width)
        draw.line([(w - 1, h - 1), (0, h - 1)], fill=fillcolor, width=width)
        draw.line([(0, h - 1), (0, 0)], fill=fillcolor, width=width)

    @staticmethod
    def __shear_x(w, h, color, draw, img):
        period = random.randint(1, 2)
        border_gap = True
        frames = 1
        phase = random.randint(1, 2)
        for i in range(h):
            d = (period >> 1) * math.sin(i / period + (6.2831853071795862 * phase) / frames)
            box_old = (0, i, w, i + 1)
            box_new = (0 + int(d), i, w + int(d), i + 1)
            region = img.crop(box=box_old)
            img.paste(region, box_new)
            if border_gap:
                draw.line([(int(d), i), (0, i)], fill=color)
                draw.line([(int(d) + w, i), (w, i)], fill=color)

    @staticmethod
    def __shear_y(w, h, color, draw, img):
        period = random.randint(1, 40) + 10
        border_gap = True
        frames = 20
        phase = 7
        for i in range(w):
            d = (period >> 1) * math.sin(i / period + (6.2831853071795862 * phase) / frames)
            box_old = (i, 0, i + 1, h)
            box_new = (i + 0, int(d), i + 1, h + int(d))
            region = img.crop(box=box_old)
            img.paste(region, box_new)
            if border_gap:
                draw.line([(i, int(d)), (i, 0)], fill=color)
                draw.line([(i, int(d) + h), (i, h)], fill=color)

    @staticmethod
    def __get_rand_color(bc, ec):
        if ec > 255:
            ec = 255
        if bc > 255:
            bc = 255
        r = bc + random.randint(0, ec - bc)
        g = bc + random.randint(0, ec - bc)
        b = bc + random.randint(0, ec - bc)
        color = (r, g, b)
        return color

    @staticmethod
    def __get_rand_rgb():
        rgb = [0, 0, 0]
        for i in range(len(rgb)):
            rgb[i] = random.randint(0, 255)
        color = 0;
        for c in rgb:
            color = color << 8
            color = color | c
        return color

    def output_image(self, w, h, size=4, sources=None):
        code = self.__gene_verify_code(size, sources)
        self.code = code
        img = self.__image_gene(w, h, code)
        return code, img
