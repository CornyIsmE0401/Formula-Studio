# -*- coding: utf-8 -*-
"""icons.py - Bộ biểu tượng vector đồng nhất (nét 1.8px, bo tròn), hỗ trợ mọi trạng thái sáng/tối."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

SIZE = 20


def _draw(name, p, col):
    pen = QPen(QColor(col), 1.85, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)

    if name == "math":          # Σ
        path = QPainterPath()
        path.moveTo(17.5, 4.5)
        path.lineTo(6.5, 4.5)
        path.lineTo(12.5, 12)
        path.lineTo(6.5, 19.5)
        path.lineTo(17.5, 19.5)
        p.drawPath(path)
    elif name == "chem":        # bình tam giác
        path = QPainterPath()
        path.moveTo(9.3, 3.5)
        path.lineTo(9.3, 9.6)
        path.lineTo(4.3, 18.2)
        path.quadTo(3.7, 19.8, 5.5, 19.8)
        path.lineTo(18.5, 19.8)
        path.quadTo(20.3, 19.8, 19.7, 18.2)
        path.lineTo(14.7, 9.6)
        path.lineTo(14.7, 3.5)
        p.drawPath(path)
        p.drawLine(QPointF(8, 3.5), QPointF(16, 3.5))
        p.drawLine(QPointF(7.3, 14.3), QPointF(16.7, 14.3))
    elif name == "calc":        # máy tính
        p.drawRoundedRect(QRectF(5, 2.8, 14, 18.4), 2.8, 2.8)
        p.drawRoundedRect(QRectF(7.8, 5.5, 8.4, 3.5), 1.1, 1.1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(col))
        for r in range(3):
            for c in range(3):
                p.drawEllipse(QPointF(8.6 + c * 3.4, 12.6 + r * 2.9), 0.95, 0.95)
    elif name == "settings":    # bánh răng
        c = QPointF(12, 12)
        p.drawEllipse(c, 3.0, 3.0)
        p.drawEllipse(c, 6.4, 6.4)
        for k in range(8):
            a = k * math.pi / 4
            p.drawLine(QPointF(12 + 6.4 * math.cos(a), 12 + 6.4 * math.sin(a)),
                       QPointF(12 + 9.1 * math.cos(a), 12 + 9.1 * math.sin(a)))
    elif name == "doc":         # tài liệu Word
        path = QPainterPath()
        path.moveTo(6, 3.5)
        path.lineTo(14, 3.5)
        path.lineTo(18.5, 8)
        path.lineTo(18.5, 20.5)
        path.lineTo(6, 20.5)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(14, 3.5), QPointF(14, 8))
        p.drawLine(QPointF(14, 8), QPointF(18.5, 8))
        p.drawLine(QPointF(9, 12.6), QPointF(15.5, 12.6))
        p.drawLine(QPointF(9, 16.2), QPointF(15.5, 16.2))
    elif name == "sun":
        p.drawEllipse(QPointF(12, 12), 4.1, 4.1)
        for k in range(8):
            a = k * math.pi / 4
            p.drawLine(QPointF(12 + 6.9 * math.cos(a), 12 + 6.9 * math.sin(a)),
                       QPointF(12 + 9.3 * math.cos(a), 12 + 9.3 * math.sin(a)))
    elif name == "moon":
        path = QPainterPath()
        path.moveTo(18.2, 14.8)
        path.arcTo(QRectF(4.2, 4.2, 15.6, 15.6), -35, -255)
        path.quadTo(11.8, 12.2, 18.2, 14.8)
        p.drawPath(path)
    elif name == "undo":
        path = QPainterPath()
        path.moveTo(8.5, 6.5)
        path.lineTo(4.5, 10.5)
        path.lineTo(8.5, 14.5)
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(5, 10.5)
        path2.lineTo(14.5, 10.5)
        path2.cubicTo(19, 10.5, 19.5, 17.5, 14.5, 17.5)
        path2.lineTo(9.5, 17.5)
        p.drawPath(path2)
    elif name == "redo":
        path = QPainterPath()
        path.moveTo(15.5, 6.5)
        path.lineTo(19.5, 10.5)
        path.lineTo(15.5, 14.5)
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(19, 10.5)
        path2.lineTo(9.5, 10.5)
        path2.cubicTo(5, 10.5, 4.5, 17.5, 9.5, 17.5)
        path2.lineTo(14.5, 17.5)
        p.drawPath(path2)
    elif name == "copy":
        p.drawRoundedRect(QRectF(8.5, 8.5, 10.5, 11.5), 2, 2)
        path = QPainterPath()
        path.moveTo(15.5, 8.5)
        path.lineTo(15.5, 6)
        path.quadTo(15.5, 4.5, 14, 4.5)
        path.lineTo(6.5, 4.5)
        path.quadTo(5, 4.5, 5, 6)
        path.lineTo(5, 14.5)
        path.quadTo(5, 16, 6.5, 16)
        path.lineTo(8.5, 16)
        p.drawPath(path)
    elif name == "trash":
        p.drawLine(QPointF(4.5, 6.5), QPointF(19.5, 6.5))
        p.drawRoundedRect(QRectF(9, 3.8, 6, 2.7), 1, 1)
        path = QPainterPath()
        path.moveTo(6.5, 6.5)
        path.lineTo(7.5, 19)
        path.quadTo(7.6, 20.2, 8.8, 20.2)
        path.lineTo(15.2, 20.2)
        path.quadTo(16.4, 20.2, 16.5, 19)
        path.lineTo(17.5, 6.5)
        p.drawPath(path)
        p.drawLine(QPointF(10.2, 10.2), QPointF(10.2, 16.8))
        p.drawLine(QPointF(13.8, 10.2), QPointF(13.8, 16.8))
    elif name == "sparkles":
        path = QPainterPath()
        path.moveTo(12, 3.5)
        path.quadTo(12, 12, 20.5, 12)
        path.quadTo(12, 12, 12, 20.5)
        path.quadTo(12, 12, 3.5, 12)
        path.quadTo(12, 12, 12, 3.5)
        p.drawPath(path)
    elif name == "zoom_in":
        p.drawEllipse(QPointF(10.5, 10.5), 6.2, 6.2)
        p.drawLine(QPointF(15.2, 15.2), QPointF(19.8, 19.8))
        p.drawLine(QPointF(8, 10.5), QPointF(13, 10.5))
        p.drawLine(QPointF(10.5, 8), QPointF(10.5, 13))
    elif name == "zoom_out":
        p.drawEllipse(QPointF(10.5, 10.5), 6.2, 6.2)
        p.drawLine(QPointF(15.2, 15.2), QPointF(19.8, 19.8))
        p.drawLine(QPointF(8, 10.5), QPointF(13, 10.5))
    elif name == "fit":
        for sx, sy in ((4.5, 4.5), (19.5, 4.5), (4.5, 19.5), (19.5, 19.5)):
            dx = 4.2 if sx < 12 else -4.2
            dy = 4.2 if sy < 12 else -4.2
            p.drawLine(QPointF(sx, sy), QPointF(sx + dx, sy))
            p.drawLine(QPointF(sx, sy), QPointF(sx, sy + dy))
    elif name == "rotate_l":
        p.drawArc(QRectF(5, 5, 14, 14), 30 * 16, 260 * 16)
        p.drawLine(QPointF(8.5, 4.5), QPointF(5.5, 7.5))
        p.drawLine(QPointF(5.5, 7.5), QPointF(9.3, 8.8))
    elif name == "rotate_r":
        p.drawArc(QRectF(5, 5, 14, 14), -110 * 16, 260 * 16)
        p.drawLine(QPointF(15.5, 4.5), QPointF(18.5, 7.5))
        p.drawLine(QPointF(18.5, 7.5), QPointF(14.7, 8.8))
    elif name == "flip_h":
        p.drawLine(QPointF(12, 4), QPointF(12, 20))
        path = QPainterPath()
        path.moveTo(9, 7)
        path.lineTo(4.5, 17)
        path.lineTo(9, 17)
        path.closeSubpath()
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(15, 7)
        path2.lineTo(19.5, 17)
        path2.lineTo(15, 17)
        path2.closeSubpath()
        p.drawPath(path2)
    elif name == "flip_v":
        p.drawLine(QPointF(4, 12), QPointF(20, 12))
        path = QPainterPath()
        path.moveTo(7, 9)
        path.lineTo(17, 4.5)
        path.lineTo(17, 9)
        path.closeSubpath()
        p.drawPath(path)
        path2 = QPainterPath()
        path2.moveTo(7, 15)
        path2.lineTo(17, 19.5)
        path2.lineTo(17, 15)
        path2.closeSubpath()
        p.drawPath(path2)
    elif name == "save":
        p.drawLine(QPointF(12, 4.5), QPointF(12, 15))
        p.drawLine(QPointF(8.2, 11.2), QPointF(12, 15))
        p.drawLine(QPointF(15.8, 11.2), QPointF(12, 15))
        path = QPainterPath()
        path.moveTo(5, 15.5)
        path.lineTo(5, 18.5)
        path.quadTo(5, 19.5, 6.2, 19.5)
        path.lineTo(17.8, 19.5)
        path.quadTo(19, 19.5, 19, 18.5)
        path.lineTo(19, 15.5)
        p.drawPath(path)
    elif name == "camera":
        p.drawRoundedRect(QRectF(4, 7, 16, 12.5), 2.5, 2.5)
        p.drawLine(QPointF(8, 7), QPointF(9.5, 4.5))
        p.drawLine(QPointF(9.5, 4.5), QPointF(14.5, 4.5))
        p.drawLine(QPointF(14.5, 4.5), QPointF(16, 7))
        p.drawEllipse(QPointF(12, 13.2), 3.3, 3.3)
    elif name == "star":
        path = QPainterPath()
        for k in range(10):
            r = 8.4 if k % 2 == 0 else 3.8
            a = -math.pi / 2 + k * math.pi / 5
            pt = QPointF(12 + r * math.cos(a), 12.5 + r * math.sin(a))
            if k == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "search":
        p.drawEllipse(QPointF(10.5, 10.5), 6.0, 6.0)
        p.drawLine(QPointF(15.0, 15.0), QPointF(19.6, 19.6))
    elif name == "globe":
        p.drawEllipse(QPointF(12, 12), 7.8, 7.8)
        p.drawEllipse(QPointF(12, 12), 3.6, 7.8)
        p.drawLine(QPointF(4.4, 12), QPointF(19.6, 12))
        p.drawLine(QPointF(5.8, 8.2), QPointF(18.2, 8.2))
        p.drawLine(QPointF(5.8, 15.8), QPointF(18.2, 15.8))
    elif name == "cursor":
        path = QPainterPath()
        path.moveTo(6.5, 4.2)
        path.lineTo(6.5, 18.5)
        path.lineTo(10.6, 14.5)
        path.lineTo(14.2, 19.8)
        path.lineTo(16.2, 18.5)
        path.lineTo(12.8, 13.3)
        path.lineTo(18.2, 13.0)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "move":        # mũi tên 4 hướng
        p.drawLine(QPointF(12, 3.8), QPointF(12, 20.2))
        p.drawLine(QPointF(3.8, 12), QPointF(20.2, 12))
        for pts in (
            ((9.4, 6.4), (12, 3.8), (14.6, 6.4)),
            ((9.4, 17.6), (12, 20.2), (14.6, 17.6)),
            ((6.4, 9.4), (3.8, 12), (6.4, 14.6)),
            ((17.6, 9.4), (20.2, 12), (17.6, 14.6)),
        ):
            path = QPainterPath()
            path.moveTo(*pts[0])
            path.lineTo(*pts[1])
            path.lineTo(*pts[2])
            p.drawPath(path)
    elif name == "plus_circle":
        p.drawEllipse(QPointF(12, 12), 7.8, 7.8)
        p.drawLine(QPointF(8.4, 12), QPointF(15.6, 12))
        p.drawLine(QPointF(12, 8.4), QPointF(12, 15.6))
    elif name == "minus_circle":
        p.drawEllipse(QPointF(12, 12), 7.8, 7.8)
        p.drawLine(QPointF(8.4, 12), QPointF(15.6, 12))
    elif name == "star_filled":
        path = QPainterPath()
        for k in range(10):
            r = 8.4 if k % 2 == 0 else 3.8
            a = -math.pi / 2 + k * math.pi / 5
            pt = QPointF(12 + r * math.cos(a), 12.5 + r * math.sin(a))
            if k == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        path.closeSubpath()
        p.setBrush(QColor(col))
        p.drawPath(path)
    elif name == "grid":
        for x in (8, 16):
            p.drawLine(QPointF(x, 4.5), QPointF(x, 19.5))
        for y in (8, 16):
            p.drawLine(QPointF(4.5, y), QPointF(19.5, y))
    elif name == "eye":
        path = QPainterPath()
        path.moveTo(3.5, 12)
        path.quadTo(12, 5, 20.5, 12)
        path.quadTo(12, 19, 3.5, 12)
        p.drawPath(path)
        p.drawEllipse(QPointF(12, 12), 2.6, 2.6)
    elif name == "ring6":
        path = QPainterPath()
        for k in range(6):
            a = -math.pi / 2 + k * math.pi / 3
            pt = QPointF(12 + 7.5 * math.cos(a), 12 + 7.5 * math.sin(a))
            if k == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QPointF(12, 12), 4.0, 4.0)


def make_icon(name, normal="#64748B", active="#FFFFFF", size=SIZE, scale=2):
    ic = QIcon()
    for col, state in ((normal, QIcon.Off), (active, QIcon.On)):
        pm = QPixmap(size * scale, size * scale)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.scale(scale * size / 24.0, scale * size / 24.0)
        _draw(name, p, col)
        p.end()
        pm.setDevicePixelRatio(float(scale))
        ic.addPixmap(pm, QIcon.Normal, state)
        ic.addPixmap(pm, QIcon.Active, state)
    return ic
