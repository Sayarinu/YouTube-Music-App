import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme

Button {
    id: root
    property bool selected: false
    property bool primary: false
    property bool destructive: false
    implicitWidth: Math.max(72, implicitContentWidth + leftPadding + rightPadding)
    implicitHeight: 38
    padding: 12
    font.family: Theme.bodyFont
    font.pixelSize: 14
    palette.buttonText: destructive ? "#f2b4b4" : (primary || selected) ? Theme.onAccent : Theme.foreground
    background: Rectangle {
        radius: height / 2
        color: root.destructive
              ? (root.down ? "#5a343c" : root.hovered ? "#432b34" : "#30232b")
              : (root.primary || root.selected)
                ? (root.down ? Theme.accent : root.hovered ? Theme.accentHover : Theme.accent)
                : (root.down ? Theme.border : root.hovered ? Theme.hover : "transparent")
        border.width: root.visualFocus ? 2 : root.selected || root.destructive ? 1 : 0
        border.color: root.visualFocus ? Theme.foreground : root.destructive ? "#754650" : root.selected ? Theme.accent : Theme.border
        Behavior on color { ColorAnimation { duration: 120 } }
    }
}
