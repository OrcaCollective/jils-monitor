'use strict';

var running = false;
var interval = null;
var seen = new Set();

function getIntervalMillis() {
    var mins = $('#mins').val();
    if (mins == null || mins <= 0) {
        alert('Expected mins to be greater than zero, but got ' + mins);
        throw 'Expected mins to be greater than zero, but got ' + mins;
    }
    return mins * 60 * 1000;
}

// Ignore notification if first run
function pollJils(firstRun) {
    $('#lastPolled').text("Updating...")
    $.getJSON('/poll', function (json) {
        for (var i = 0; i < json.length; i++) {
            var record = json[i];
            var text = textFromRecord(record);

            if (!firstRun && !seen.has(record.ucn)) {
                notify(text);
                addResult(record);
            }

            seen.add(record.ucn);
        }

        $('#lastPolled').text(new Date().toLocaleTimeString());
    }).fail(function () {
        $('#lastPolled').html(
            '<span class="text-danger">'
            + new Date().toString()
            + ' (Failed!)</span>'
        );
    });
}

function textFromRecord(record) {
    return record.name + ' booked at ' + record.facility
      + " at " + record.book_date + " (UCN#: " + record.ucn + ")";
}

function notify(text) {
    if (!('Notification' in window)
            || Notification.permission !== 'granted') {
        alert(text);
    } else {
        new Notification("New Record Found!", {
            body: text
        });
    }
}

function addResult(record) {
    var result = $('<tr />');
    result.append($("<td />").text(record.book_date));
    result.append($("<td />").text(record.name));
    result.append($("<td />").text(record.ucn));
    result.append($("<td />").text(record.facility));
    var removeResult = $('<td />')
            .addClass('remove-result pl-2 text-danger')
            .text('x');
    removeResult.click(function (evt) {
        $(evt.target.parentElement).remove();
    });
    result.append(removeResult);
  
    $('#results').append(result);
}

$('#btn-go').click(function () {
    if (running) {
        clearInterval(interval);
        $('#btn-go').text('Go');
        $('#btn-go').addClass('btn-primary');
        $('#btn-go').removeClass('btn-danger');
    } else {
        interval = setInterval(pollJils, getIntervalMillis())
        $('#btn-go').text('Stop');
        $('#btn-go').addClass('btn-danger');
        $('#btn-go').removeClass('btn-primary');

        pollJils(true);
    }
    $('#mins').prop('disabled', !running);
    running = !running;
});

$('#btn-clear').click(function () {
    $('#results').empty();
});

Notification.requestPermission();