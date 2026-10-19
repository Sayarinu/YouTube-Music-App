import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme

MenuItem {
    id: root
    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
    contentItem: Text {
        text: root.text
        textFormat: Text.PlainText
        color: root.enabled ? Theme.foreground : Theme.muted
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: 8
        color: root.highlighted || root.hovered ? Theme.hover : "transparent"
        border.color: root.visualFocus ? Theme.accent : "transparent"
        Behavior on color { ColorAnimation { duration: 100 } }
    }
}
