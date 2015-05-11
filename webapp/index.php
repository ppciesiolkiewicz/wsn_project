<?php
$mysql_host = 'localhost';
$username = 'root';
$password = 'rasproot';
$database = 'wsn_measurements';
 
try {
    $pdo = new PDO('mysql:host='.$mysql_host.';dbname='.$database.';port='.$port, $username, $password );
} catch(PDOException $e) {
    echo $e->getMessage();
}

    $measurements = array();
    $stmt = $pdo->query('SELECT `from` FROM measurement GROUP BY `from`;');
    foreach($stmt as $row) {
        $measurements[$row['from']] = array();
        $measurements[$row['from']]['timestamp'] = array();
        $measurements[$row['from']]['temp'] = array();
        $measurements[$row['from']]['hum'] = array();
        $measurements[$row['from']]['photo'] = array();

        $stmt_measurements = $pdo->query('SELECT UNIX_TIMESTAMP(`timestamp`) as `timestamp`, `temp`, `hum`, `photo` 
                             FROM measurement WHERE `from`=' . $row['from'] . ';');
        foreach($stmt_measurements as $m) {
            $measurements[$row['from']]['timestamp'][] = $m['timestamp'];
            $measurements[$row['from']]['temp'][] = $m['temp'];
            $measurements[$row['from']]['hum'][] = $m['hum'];
            $measurements[$row['from']]['photo'][] = $m['photo'];
        }
    }


    /*
    Array structure
    Array
    (
        [sensorNo] => Array
        (
             [values_name] => Array
                (
                    [0] => val_1
                    [1] => val_2
                )
        )
    )
    xName is always a timestamp.
    */
    function generateSeries($yName, $arrOfSensors) {
        echo 'series = [';
        foreach($arrOfSensors as $sensor => $arr) {
            echo '{';
            echo 'name: "sensor ' . $sensor . '",';
            echo 'data:';
            echo '[';
            for ($i = 0; $i < count($arr['timestamp']) ; $i++) {
                echo '['.$arr['timestamp'][$i].'000,'.$arr[$yName][$i] . '],';
            }
            echo ']';
            echo '},';
        }
        echo '];';
    }
?>
<html>
<head>
<!-- jquery -->
<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.3/jquery.min.js"></script>
<!-- jquery UI-->
<script src="//code.jquery.com/ui/1.11.4/jquery-ui.js"></script>
<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
<!-- Latest compiled and minified bootstrap JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js"></script>

<!-- Highcharts -->
<script src="http://code.highcharts.com/highcharts.js"></script>
<script src="http://code.highcharts.com/modules/data.js"></script>
<script src="http://code.highcharts.com/modules/exporting.js"></script>
<script>
$(function () {
    $( "#tabs" ).tabs();
    var <?php generateSeries("temp", $measurements); ?>
    render(series, "#temperature", "Temperature", "temperature [*C]");

    <?php generateSeries("hum", $measurements); ?>
    render(series, "#humidity", "Humidity", "humidity [%]");

    <?php generateSeries("photo", $measurements); ?>
    render(series, "#photo", "Photo", "photo [lux]");
});

function render(series_, renderTo_, title_, yAxisTitle_) {
    $(renderTo_).highcharts({
        chart: {
            type: 'spline',
            zoomType: 'x'
        },
        title: {
            text: title_
        },
        xAxis: {
            type: 'datetime',
            dateTimeLabelFormats: { // don't display the dummy year
                month: '%e. %b',
                year: '%b'
            },
            title: {
                text: 'Date'
            }
        },
        yAxis: {
            title: {
                text: yAxisTitle_
            },
            min: 0
        },
        tooltip: {
            headerFormat: '<b>{series.name}</b><br>',
            pointFormat: '{point.x:%e. %b}: {point.y:.2f} m'
        },

        plotOptions: {
            spline: {
                marker: {
                    enabled: true
                }
            }
        },
        credits: {
            enabled: false
        },

        series: series_
    });
}
</script>
</head>
<body>
<div id="tabs">
  <ul>
    <li class="btn btn-default"><a href="#tabs-1">Temperature</a></li>
    <li class="btn btn-default"><a href="#tabs-2">Humidity</a></li>
    <li class="btn btn-default"><a href="#tabs-3">Photo</a></li>
  </ul>
  <div id="tabs-1">
    <div id="temperature"></div>
  </div>
  <div id="tabs-2">
    <div id="humidity"></div>
  </div>
  <div id="tabs-3">
    <div id="photo"></div>
  </div>
</div>


</body>
</html>
