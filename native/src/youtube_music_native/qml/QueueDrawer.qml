import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Rectangle {
    id: root
    objectName: "queueDrawer"
    color: Theme.surface
    radius: 14
    border.color: Theme.border
    border.width: 1

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 16
        spacing: 8
        RowLayout {
            Layout.fillWidth: true
            Text { text: "Queue"; color: Theme.foreground; font.family: Theme.headingFont; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true }
            IconButton { iconName: "close"; tip: "Close queue"; onClicked: appState.setQueueOpen(false) }
        }
        RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2
                Text { text: "Autoplay"; color: Theme.foreground; font.pixelSize: 14 }
                Text { text: "Add similar music"; color: Theme.secondary; font.pixelSize: 12 }
            }
            Switch {
                id: autoplaySwitch
                checked: playerState.autoplay
                Accessible.name: "Autoplay similar music"
                onClicked: playerState.toggleAutoplay()
                indicator: Rectangle {
                    implicitWidth: 40; implicitHeight: 24; x: autoplaySwitch.leftPadding; y: (autoplaySwitch.height - height) / 2
                    radius: 12; color: autoplaySwitch.checked ? Theme.accent : Theme.border
                    border.width: autoplaySwitch.visualFocus ? 2 : 0; border.color: Theme.foreground
                    Rectangle { x: autoplaySwitch.checked ? parent.width - width - 3 : 3; y: 3; width: 18; height: 18; radius: 9; color: autoplaySwitch.checked ? Theme.onAccent : Theme.secondary }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Item { Layout.fillWidth: true }
            StateButton {
                text: "Clear queue"
                implicitHeight: 34
                enabled: playerState.manualCount > 0 || browseState.queueBusy
                onClicked: playerState.clearManualQueue()
            }
        }
        ListView {
            id: queue
            objectName: "queueDrawerList"
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: playerState.entries
            section.property: "group"
            section.criteria: ViewSection.FullString
            section.delegate: Text {
                required property string section
                width: queue.width; height: 36; topPadding: 12
                text: section; textFormat: Text.PlainText; elide: Text.ElideRight
                color: Theme.accent; font.pixelSize: 13; font.bold: true
            }
            ScrollBar.vertical: ScrollBar {}
            delegate: Item {
                required property var modelData
                width: queue.width; height: 64
                Rectangle { anchors.fill: parent; radius: 8; color: modelData.current ? Theme.selected : "transparent" }
                SongRow {
                    anchors.fill: parent; anchors.rightMargin: 38
                    media: modelData
                    subtitle: modelData.artist || ""
                    menuContext: ({queueKey: modelData.key})
                    onActivated: playerState.selectKey(modelData.key)
                }
                IconButton {
                    anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                    iconName: "more"; tip: "Queue actions for " + (modelData.title || "song")
                    onClicked: appState.showMenu(modelData, {queueKey: modelData.key})
                }
            }
            Text {
                anchors.centerIn: parent; width: parent.width
                visible: queue.count === 0; text: "Your queue is empty"
                color: Theme.secondary; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.Wrap
            }
        }
    }
}
