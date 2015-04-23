CREATE TABLE IF NOT EXISTS `wsn_measurements`.`measurement` (
  `timestamp` DATETIME NOT NULL,
  `from` INT NOT NULL,
  `to` INT NOT NULL,
  `seq_no` INT NULL,
  `hops` INT NULL,
  `batt` FLOAT NULL,
  `debug2_1` INT NULL,
  `debug2_2` INT NULL,
  `debug2_3` INT NULL,
  `debug2_4` INT NULL,
  `debug2_5` INT NULL,
  `hum` FLOAT NULL,
  `msg_type` INT NOT NULL,
  `photo` FLOAT NULL,
  `temp` FLOAT NULL,
  `measurement_id` INT NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`measurement_id`))
ENGINE = InnoDB;
