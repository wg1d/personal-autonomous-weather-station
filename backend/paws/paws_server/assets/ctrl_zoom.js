/*
 * Zoom of the graphs with Ctrl + mouse wheel.
 *
 * Plotly zooms on every turn of the wheel over the graphs (scrollZoom),
 * which would catch the wheel while scrolling down the page. This listener
 * runs before Plotly (capture phase) and stops the wheel events without
 * Ctrl: the page scrolls as usual, and only Ctrl + wheel reaches Plotly.
 */
document.addEventListener("wheel", function (event) {
    var graph = document.getElementById("graph");
    if (graph && graph.contains(event.target) && !event.ctrlKey) {
        event.stopPropagation();
    }
}, { capture: true });
