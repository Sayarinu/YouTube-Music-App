import QtQuick
import QtQuick.Controls

SurfaceMenu {
    id: root
    objectName: "mediaMenu"
    property var media: ({})
    property var context: ({})
    property bool song: media.kind === "song" || !!media.videoId
    property bool queueable: song || media.kind === "album" || media.kind === "playlist"
    property bool canEdit: (accountState.connected || appState.fixtureMode) && !accountState.busy && !actionsState.busy
    property bool playlistEntry: song && !!media.setVideoId && catalogState.route === "playlist" && catalogState.data.editable && context.playlistId === catalogState.parameters.id
    MenuAction { text: "Play"; onTriggered: { if (root.context.queueKey) playerState.selectKey(root.context.queueKey); else browseState.play(root.media) } }
    MenuAction { text: "Play next"; visible: root.queueable; height: visible ? implicitHeight : 0; onTriggered: browseState.enqueue(root.media, true) }
    MenuAction { text: "Add to queue"; visible: root.queueable; height: visible ? implicitHeight : 0; onTriggered: browseState.enqueue(root.media, false) }
    MenuAction { text: "Start radio"; visible: root.song; height: visible ? implicitHeight : 0; onTriggered: browseState.startRadioForSong(root.media.videoId || root.media.id) }
    MenuSeparator { visible: root.song; height: visible ? implicitHeight : 0 }
    MenuAction { text: root.media.rating === "LIKE" ? "Remove like" : "Like"; visible: root.song; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.rate(root.media, "LIKE") }
    MenuAction { text: root.media.rating === "DISLIKE" ? "Remove dislike" : "Dislike"; visible: root.song; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.rate(root.media, "DISLIKE") }
    MenuAction { text: root.media.inLibrary ? "Remove from library" : "Save to library"; visible: root.song; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.saveSong(root.media) }
    MenuAction { text: "Add to playlist"; visible: root.song; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.choosePlaylist(root.media) }
    MenuAction { text: "Download"; visible: root.media.kind !== "artist"; height: visible ? implicitHeight : 0; onTriggered: downloadsState.download(root.media) }
    MenuAction { text: "Go to album"; visible: root.song && !!(root.media.album && root.media.album.id); height: visible ? implicitHeight : 0; onTriggered: browseState.open({kind: "album", id: root.media.album.id}) }
    MenuAction { text: "Go to artist"; visible: root.song && !!(root.media.artists && root.media.artists.length && root.media.artists[0].id); height: visible ? implicitHeight : 0; onTriggered: browseState.open({kind: "artist", id: root.media.artists[0].id}) }
    MenuSeparator { visible: root.playlistEntry || (root.media.kind === "playlist" && root.media.owned); height: visible ? implicitHeight : 0 }
    MenuAction { text: "Remove from playlist"; visible: root.playlistEntry; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.removeEntry(root.media) }
    MenuAction { text: "Move up"; visible: root.playlistEntry; height: visible ? implicitHeight : 0; enabled: root.canEdit && !catalogState.busy && root.context.index > 0; onTriggered: libraryState.moveEntry(root.media, -1) }
    MenuAction { text: "Move down"; visible: root.playlistEntry; height: visible ? implicitHeight : 0; enabled: root.canEdit && !catalogState.busy && (root.context.index + 1 < (catalogState.data.items || []).length || catalogState.data.cursor !== undefined && catalogState.data.cursor !== null); onTriggered: libraryState.moveEntry(root.media, 1) }
    MenuAction { text: "Rename playlist"; visible: root.media.kind === "playlist" && root.media.owned; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.edit("playlist_rename", root.media) }
    MenuAction { text: "Delete playlist"; visible: root.media.kind === "playlist" && root.media.owned; height: visible ? implicitHeight : 0; enabled: root.canEdit; onTriggered: libraryState.edit("playlist_delete", root.media) }
    MenuSeparator { visible: !!root.context.queueKey; height: visible ? implicitHeight : 0 }
    MenuAction { text: "Remove from queue"; visible: !!root.context.queueKey; height: visible ? implicitHeight : 0; onTriggered: playerState.removeKey(root.context.queueKey) }
    MenuAction { text: "Move up in queue"; visible: !!root.context.queueKey && !!root.media.movable; height: visible ? implicitHeight : 0; onTriggered: playerState.moveKey(root.context.queueKey, -1) }
    MenuAction { text: "Move down in queue"; visible: !!root.context.queueKey && !!root.media.movable; height: visible ? implicitHeight : 0; onTriggered: playerState.moveKey(root.context.queueKey, 1) }
}
