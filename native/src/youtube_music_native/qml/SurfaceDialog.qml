import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme

Dialog {
    id: root
    padding: 24
    background: Rectangle { radius: 16; color: Theme.surface; border.color: Theme.border }
    header: Label {
        text: root.title
        visible: text.length > 0
        textFormat: Text.PlainText
        color: Theme.foreground
        font.pixelSize: 22
        font.bold: true
        wrapMode: Text.Wrap
        leftPadding: 24; rightPadding: 24; topPadding: 24; bottomPadding: 4
    }
    footer: DialogButtonBox {
        padding: 16
        spacing: 8
        standardButtons: root.standardButtons
        visible: count > 0
        delegate: ActionButton {}
        background: Item {}
    }
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140; easing.type: Easing.OutCubic } }
}
