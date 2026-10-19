import QtQuick
import QtQuick.Controls
import "Theme.js" as Theme

FocusScope {
    id: root
    required property var media
    property int number: 0
    property bool showArtwork: true
    property bool showDuration: !showArtwork
    property bool tableLayout: false
    property bool showAlbum: false
    property var menuContext: ({})
    property string downloadStatus: downloadsState.trackStates[media.videoId || media.id] || media.downloadState || ""
    property string subtitle: {
        var label = media.kind && media.kind !== "song" ? media.kind.charAt(0).toUpperCase() + media.kind.slice(1) : ""
        if (media.artist) label += (label ? " · " : "") + media.artist
        if (media.album && media.album.name) label += (label ? " · " : "") + media.album.name
        return label
    }
    signal activated(var item)
    signal menuRequested(var item)
    onMenuRequested: item => appState.showMenu(item, menuContext)
    implicitHeight: 64
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: (media.title || "Song") + ", " + (media.artist || "")
    Accessible.description: downloadStatus === "ready" ? "Downloaded" : downloadStatus === "damaged" || downloadStatus === "missing" ? "Download needs repair" : downloadStatus === "downloading" || downloadStatus === "queued" ? "Downloading" : ""
    Accessible.onPressAction: activated(media)
    Keys.onReturnPressed: activated(media)
    Keys.onPressed: event => { if (event.key === Qt.Key_Menu || event.key === Qt.Key_F10 && event.modifiers & Qt.ShiftModifier) { root.menuRequested(root.media); event.accepted = true } }
    Rectangle { anchors.fill: parent; radius: 4; color: hover.hovered ? "#1affffff" : "transparent"; border.color: root.activeFocus ? Theme.accent : "transparent"; border.width: 1 }
    Cover { id: art; visible: root.showArtwork; x: root.tableLayout ? 44 : 8; anchors.verticalCenter: parent.verticalCenter; width: root.tableLayout ? 40 : 48; height: width; radius: root.media.kind === "artist" ? width / 2 : 6; placeholder: root.media.kind === "artist" ? "profile" : "music"; source: root.media.thumbnail || ""; mediaKey: root.media.videoId || root.media.id || ""; accent: root.media.accent || Theme.selected; Symbol { anchors.centerIn: parent; name: "play"; width: 28; height: 28; visible: root.media.kind !== "artist" && (hover.hovered || root.activeFocus) } }
    Text { id: rank; x: root.tableLayout ? 12 : root.showArtwork ? 68 : 16; width: root.number > 0 ? 28 : 0; visible: root.number > 0; anchors.verticalCenter: parent.verticalCenter; text: root.number; color: Theme.secondary; font.pixelSize: 14 }
    Column {
        x: root.tableLayout ? root.showArtwork ? 100 : 48 : root.showArtwork ? root.number > 0 ? 104 : 72 : 56
        anchors.verticalCenter: parent.verticalCenter
        width: (root.showAlbum ? parent.width * 0.54 : parent.width - (root.showDuration ? 112 : 56)) - x; spacing: 3
        opacity: root.media.available === false ? 0.5 : 1
        Text { width: parent.width; text: root.media.title || "Unavailable song"; textFormat: Text.PlainText; elide: Text.ElideRight; color: hover.hovered ? Theme.accentHover : Theme.foreground; font.pixelSize: 14; font.underline: hover.hovered }
        Row {
            width: parent.width; spacing: 6
            Symbol { id: downloaded; width: 16; height: 16; visible: !!root.downloadStatus; name: root.downloadStatus === "ready" ? "check" : "download"; color: root.downloadStatus === "damaged" || root.downloadStatus === "missing" ? "#ffb4a6" : Theme.secondary }
            Text {
                visible: root.showArtwork && !root.tableLayout && !!(root.media.kind && root.media.kind !== "song")
                text: visible ? root.media.kind.charAt(0).toUpperCase() + root.media.kind.slice(1) : ""
                textFormat: Text.PlainText; color: Theme.secondary; font.pixelSize: 14
            }
            Text { visible: root.showArtwork && !root.tableLayout && root.media.kind && root.media.kind !== "song" && (artistLink.visible || !!root.media.artist); text: "·"; color: Theme.secondary; font.pixelSize: 14 }
            Button {
                id: artistLink
                z: 2
                visible: !!(root.media.artists && root.media.artists.length && root.media.artists[0].id)
                text: visible ? root.media.artists[0].name || root.media.artist || "" : ""
                width: Math.min(160, parent.width * 0.55)
                padding: 0; leftPadding: 0; rightPadding: 0; flat: true
                implicitHeight: 20
                enabled: visible
                Accessible.name: "Open artist " + text
                contentItem: Text { text: artistLink.text; textFormat: Text.PlainText; color: artistLink.hovered ? Theme.foreground : Theme.secondary; font.pixelSize: 14; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; font.underline: artistLink.hovered }
                onClicked: browseState.open({kind: "artist", id: root.media.artists[0].id, title: text})
            }
            Text {
                visible: !artistLink.visible
                width: Math.min(200, parent.width * 0.65)
                text: root.media.artist || (root.media.views ? root.media.views + " plays" : "")
                textFormat: Text.PlainText; elide: Text.ElideRight; color: Theme.secondary; font.pixelSize: 14
            }
            Text { visible: artistLink.visible && root.showArtwork && !root.tableLayout && albumLink.visible; text: "·"; color: Theme.secondary; font.pixelSize: 14 }
            Button {
                id: albumLink
                z: 2
                visible: root.showArtwork && !root.tableLayout && !!(root.media.album && root.media.album.id)
                text: visible ? root.media.album.name || "" : ""
                width: Math.min(160, parent.width * 0.48)
                padding: 0; leftPadding: 0; rightPadding: 0; flat: true
                implicitHeight: 20
                Accessible.name: "Open album " + text
                contentItem: Text { text: albumLink.text; textFormat: Text.PlainText; color: albumLink.hovered ? Theme.foreground : Theme.secondary; font.pixelSize: 14; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; font.underline: albumLink.hovered }
                onClicked: browseState.open({kind: "album", id: root.media.album.id, title: text})
            }
        }
    }
    Button {
        id: tableAlbumLink
        z: 2
        x: parent.width * 0.56; width: parent.width * 0.44 - 120; height: 36; anchors.verticalCenter: parent.verticalCenter
        visible: root.showAlbum
        text: root.media.album ? root.media.album.name || "" : ""
        enabled: !!(root.media.album && root.media.album.id)
        padding: 0; leftPadding: 0; rightPadding: 0; flat: true
        Accessible.name: "Open album " + text
        contentItem: Text { text: tableAlbumLink.text; textFormat: Text.PlainText; elide: Text.ElideRight; color: tableAlbumLink.hovered ? Theme.foreground : Theme.secondary; font.pixelSize: 13; verticalAlignment: Text.AlignVCenter; font.underline: tableAlbumLink.hovered }
        onClicked: browseState.open({kind: "album", id: root.media.album.id, title: text})
    }
    Text { anchors.right: parent.right; anchors.rightMargin: 56; anchors.verticalCenter: parent.verticalCenter; visible: root.showDuration; text: root.media.duration ? Theme.timeLabel(root.media.duration) : "–"; color: Theme.secondary; font.pixelSize: 13 }
    HoverHandler { id: hover }
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.LeftButton | Qt.RightButton; cursorShape: Qt.PointingHandCursor; onClicked: function(mouse) { if (mouse.button === Qt.RightButton) root.menuRequested(root.media); else root.activated(root.media) } }
    IconButton { anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter; iconName: "more"; tip: "More options for " + (root.media.title || "song"); visible: hover.hovered || root.activeFocus; onClicked: root.menuRequested(root.media) }
}
