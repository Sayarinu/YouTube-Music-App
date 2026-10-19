import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Theme.js" as Theme

Item {
    id: root
    property bool opened: editor.opened || removal.opened || chooser.opened
    property string operation: "playlist_create"
    property var target: ({})
    property string privacy: "PRIVATE"
    Dialog {
        id: editor
        objectName: "playlistEditor"
        anchors.centerIn: parent; width: Math.min(root.width - 80, 440); modal: true
        title: root.operation === "playlist_create" ? "New playlist" : "Rename playlist"
        palette.window: Theme.surface; palette.windowText: "white"; palette.text: "white"
        contentItem: ColumnLayout {
            spacing: 16
            TextField { id: name; objectName: "playlistNameField"; Layout.fillWidth: true; maximumLength: 150; placeholderText: "Playlist name"; color: "white"; placeholderTextColor: Theme.secondary; selectByMouse: true; Accessible.name: "Playlist name"; background: Rectangle { color: Theme.hover; radius: 4; border.color: name.activeFocus ? "white" : Theme.muted } onAccepted: if (save.enabled) save.clicked() }
            ColumnLayout {
                Layout.fillWidth: true
                visible: root.operation === "playlist_create"
                spacing: 8
                Label { text: "Who can see this playlist?"; color: Theme.secondary }
                RowLayout {
                    spacing: 8
                    ActionButton { text: "Private"; selected: root.privacy === "PRIVATE"; onClicked: root.privacy = "PRIVATE" }
                    ActionButton { text: "Unlisted"; selected: root.privacy === "UNLISTED"; onClicked: root.privacy = "UNLISTED" }
                    ActionButton { text: "Public"; selected: root.privacy === "PUBLIC"; onClicked: root.privacy = "PUBLIC" }
                }
            }
            Label { Layout.fillWidth: true; text: actionsState.message; textFormat: Text.PlainText; visible: !!text; wrapMode: Text.Wrap; color: Theme.secondary }
        }
        footer: RowLayout {
            spacing: 10
            Item { Layout.fillWidth: true }
            ActionButton { text: "Cancel"; implicitWidth: 92; enabled: !actionsState.busy; onClicked: editor.close() }
            ActionButton { id: save; text: "Save"; primary: true; implicitWidth: 76; enabled: !!name.text.trim() && !actionsState.busy && (accountState.connected || appState.fixtureMode); onClicked: if (root.operation === "playlist_create") libraryState.create(name.text, root.privacy); else libraryState.rename(root.target.id, name.text) }
        }
        onRejected: editor.close()
        onOpened: { name.forceActiveFocus(); name.selectAll(); if (root.operation === "playlist_create") root.privacy = "PRIVATE" }
    }
    Dialog {
        id: removal
        anchors.centerIn: parent; width: Math.min(root.width - 80, 440); modal: true
        title: "Delete playlist"
        palette.window: Theme.surface; palette.windowText: "white"; palette.text: "white"
        contentItem: ColumnLayout {
            spacing: 16
            Label { Layout.fillWidth: true; text: "Delete “" + (root.target.title || "this playlist") + "” from YouTube Music?"; textFormat: Text.PlainText; wrapMode: Text.Wrap; color: "white" }
            Label { Layout.fillWidth: true; text: actionsState.message; textFormat: Text.PlainText; visible: !!text; wrapMode: Text.Wrap; color: Theme.secondary }
        }
        footer: RowLayout {
            spacing: 10
            Item { Layout.fillWidth: true }
            ActionButton { text: "Cancel"; implicitWidth: 92; enabled: !actionsState.busy; onClicked: removal.close() }
            ActionButton { text: "Delete"; destructive: true; implicitWidth: 84; enabled: !actionsState.busy && (accountState.connected || appState.fixtureMode); onClicked: libraryState.removePlaylist(root.target.id) }
        }
        onRejected: removal.close()
    }
    Dialog {
        id: chooser
        anchors.centerIn: parent; width: Math.min(root.width - 80, 440); modal: true
        title: "Add to playlist"; standardButtons: Dialog.Cancel
        palette.window: Theme.surface; palette.windowText: "white"; palette.text: "white"
        contentItem: ColumnLayout {
            spacing: 16
            TextField { id: find; Layout.fillWidth: true; placeholderText: "Find a playlist"; color: "white"; placeholderTextColor: Theme.secondary; Accessible.name: "Find a playlist"; background: Rectangle { color: Theme.hover; radius: 4 } }
            ListView {
                Layout.fillWidth: true; Layout.preferredHeight: 280; clip: true; model: libraryState.playlists
                ScrollBar.vertical: ScrollBar {}
                delegate: ItemDelegate {
                    required property var modelData
                    width: ListView.view.width; height: visible ? 48 : 0; visible: !find.text || modelData.title.toLowerCase().indexOf(find.text.toLowerCase()) >= 0
                    enabled: !actionsState.busy && (accountState.connected || appState.fixtureMode)
                    contentItem: Text { text: modelData.title; textFormat: Text.PlainText; color: "white"; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                    onClicked: libraryState.add(modelData.id, root.target)
                }
            }
            BusyIndicator { Layout.alignment: Qt.AlignHCenter; running: libraryState.loadingPlaylists; visible: running }
            Label { Layout.fillWidth: true; text: actionsState.message || libraryState.message || (!libraryState.loadingPlaylists && !libraryState.playlists.length ? "Create a playlist with New playlist, then add this song." : ""); textFormat: Text.PlainText; visible: !!text; wrapMode: Text.Wrap; color: Theme.secondary }
            Button { text: "Retry"; visible: !!libraryState.message; onClicked: libraryState.choosePlaylist(root.target) }
        }
    }
    Connections {
        target: libraryState
        function onDialogRequested(operation, media) { actionsState.dismiss(); root.operation = operation; root.target = media; if (operation === "playlist_delete") removal.open(); else { name.text = media.title || ""; editor.open() } }
        function onChooserRequested(media) { actionsState.dismiss(); root.target = media; find.clear(); chooser.open() }
        function onEditFinished() { editor.close(); removal.close(); chooser.close() }
    }
}
