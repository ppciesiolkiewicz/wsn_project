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
        $measurements[$row['from']]['photo'][] = array();

        $stmt_measurements = $pdo->query('SELECT UNIX_TIMESTAMP(`timestamp`) as `timestamp`, `temp`, `hum`, `photo` 
                             FROM measurement WHERE `from`=' . $row['from'] . ';');
        foreach($stmt_measurements as $m) {
            $measurements[$row['from']]['timestamp'][] = $m['timestamp'];
            $measurements[$row['from']]['temp'][] = $m['temp'];
            $measurements[$row['from']]['hum'][] = $m['hum'];
            $measurements[$row['from']]['photo'][] = $M['photo'];
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
    */
    function generateSeries($xName, $yName, $arrOfSensors) {
        echo 'series = [';
        foreach($arrOfSensors as $sensor => $arr) {
            echo '{';
            echo 'name: "sensor ' . $sensor . '",';
            echo 'data:';
            echo '[';
            for ($i = 0; $i < count($arr['timestamp']) ; $i++) {
                echo '['.$arr['timestamp'][$i].'000,'.$arr['temp'][$i] . '],';
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
<!-- Latest compiled and minified CSS -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap.min.css">
<!-- Optional theme -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/css/bootstrap-theme.min.css">
<!-- Latest compiled and minified JavaScript -->
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js"></script>

<!-- Highcharts -->
<script src="http://code.highcharts.com/highcharts.js"></script>
<script src="http://code.highcharts.com/modules/data.js"></script>
<script src="http://code.highcharts.com/modules/exporting.js"></script>
<script>
$(function () {
    var <?php generateSeries("timestamp","temp", $measurements); ?>
    render(series, "#temperature");

    <?php generateSeries("timestamp","hum", $measurements); ?>
    render(series, "#photo");

    <?php generateSeries("timestamp","photo", $measurements); ?>
    render(series, "#humidity");
});

function render(series_, renderTo_) {
    $(renderTo_).highcharts({
        chart: {
            type: 'spline'
        },
        title: {
            text: 'Temperature, Humidity and Photo for sensor <?php ?>'
        },
        subtitle: {
            text: ''
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
                text: 'Temp in Celcius, Humidity in %'
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

        series: series_
    });
}
</script>
</head>
<body>

<div id="temperature"></div>
<div id="humidity"></div>
<div id="photo"></div>

</body>
</html>
