import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme

Menu {
    width: 256
    padding: 8
    background: Rectangle { color: Theme.surface; radius: 12; border.color: Theme.border }
    delegate: MenuAction {}
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 120 } }
    exit: Transition { NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 80 } }
}
