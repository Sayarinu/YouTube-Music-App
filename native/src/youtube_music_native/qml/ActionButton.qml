import QtQuick
import QtQuick.Controls as Controls
import "Theme.js" as Theme

Controls.Button {
    id: root
    property bool primary: false
    implicitHeight: 36
    implicitWidth: Math.max(64, implicitContentWidth + leftPadding + rightPadding)
    leftPadding: 16
    rightPadding: 16
    topPadding: flat ? 2 : 8
    bottomPadding: flat ? 2 : 8
    palette.buttonText: primary ? Theme.onAccent : Theme.foreground
    contentItem: Text {
        text: root.text
        textFormat: Text.PlainText
        font: root.font
        color: root.enabled ? root.palette.buttonText : Theme.muted
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
    background: Rectangle {
        radius: height / 2
        color: root.down ? Theme.selected : root.primary ? (root.hovered ? Theme.accentHover : Theme.accent) : root.hovered ? Theme.hover : "transparent"
        border.width: root.visualFocus ? 2 : root.flat || root.primary ? 0 : 1
        border.color: root.visualFocus ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
