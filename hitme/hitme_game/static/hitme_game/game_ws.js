$(function(){
    var script_tag = document.getElementById('websocket_js');
	var url = script_tag.getAttribute("data-game");
	
	var gameSocket = new WebSocket(
        'ws://' + window.location.host +
        '/ws/game/' + url + '/');

	window.onbeforeunload = function() {
    	gameSocket.onclose = function () {}; // disable onclose handler first
    	gameSocket.close();
	};
 });
