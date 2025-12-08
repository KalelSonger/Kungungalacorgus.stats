-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: localhost    Database: spotifyDatabase
-- ------------------------------------------------------
-- Server version	8.0.44-0ubuntu0.22.04.1

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `Album_Song`
--

DROP TABLE IF EXISTS `Album_Song`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Album_Song` (
  `A_ID` varchar(50) NOT NULL,
  `S_ID` varchar(50) NOT NULL,
  PRIMARY KEY (`A_ID`,`S_ID`),
  KEY `S_ID` (`S_ID`),
  CONSTRAINT `Album_Song_ibfk_1` FOREIGN KEY (`A_ID`) REFERENCES `Albums` (`A_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `Album_Song_ibfk_2` FOREIGN KEY (`S_ID`) REFERENCES `Songs` (`S_ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Album_Song`
--

LOCK TABLES `Album_Song` WRITE;
/*!40000 ALTER TABLE `Album_Song` DISABLE KEYS */;
/*!40000 ALTER TABLE `Album_Song` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Albums`
--

DROP TABLE IF EXISTS `Albums`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Albums` (
  `A_ID` varchar(50) NOT NULL,
  `A_Title` varchar(500) NOT NULL,
  `A_Listen_Time` BIGINT DEFAULT 0,
  `A_Listens` INT DEFAULT 0,
  `A_Length` BIGINT DEFAULT 0,
  `image_url` VARCHAR(500) DEFAULT NULL,
  `A_Blacklisted_Listens` INT DEFAULT 0,
  `A_Blacklisted_Time` BIGINT DEFAULT 0,
  PRIMARY KEY (`A_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Albums`
--

LOCK TABLES `Albums` WRITE;
/*!40000 ALTER TABLE `Albums` DISABLE KEYS */;
/*!40000 ALTER TABLE `Albums` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Artists`
--

DROP TABLE IF EXISTS `Artists`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Artists` (
  `A_ID` varchar(50) NOT NULL,
  `A_Name` varchar(500) NOT NULL,
  `A_Listens` INT DEFAULT 0,
  `A_Listen_Time` BIGINT DEFAULT 0,
  `image_url` VARCHAR(500) DEFAULT NULL,
  `A_Blacklisted_Listens` INT DEFAULT 0,
  `A_Blacklisted_Time` BIGINT DEFAULT 0,
  PRIMARY KEY (`A_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Artists`
--

LOCK TABLES `Artists` WRITE;
/*!40000 ALTER TABLE `Artists` DISABLE KEYS */;
/*!40000 ALTER TABLE `Artists` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Creates`
--

DROP TABLE IF EXISTS `Creates`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Creates` (
  `ART_ID` varchar(50) NOT NULL,
  `S_ID` varchar(50) NOT NULL,
  `A_ID` varchar(50) NOT NULL,
  PRIMARY KEY (`ART_ID`,`S_ID`,`A_ID`),
  KEY `A_ID` (`A_ID`),
  KEY `S_ID` (`S_ID`),
  CONSTRAINT `Creates_ibfk_1` FOREIGN KEY (`ART_ID`) REFERENCES `Artists` (`A_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `Creates_ibfk_2` FOREIGN KEY (`A_ID`) REFERENCES `Albums` (`A_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `Creates_ibfk_3` FOREIGN KEY (`S_ID`) REFERENCES `Songs` (`S_ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Creates`
--

LOCK TABLES `Creates` WRITE;
/*!40000 ALTER TABLE `Creates` DISABLE KEYS */;
/*!40000 ALTER TABLE `Creates` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Playlist_Songs`
--

DROP TABLE IF EXISTS `Playlist_Songs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Playlist_Songs` (
  `P_ID` varchar(50) NOT NULL,
  `S_ID` varchar(50) NOT NULL,
  PRIMARY KEY (`P_ID`,`S_ID`),
  KEY `S_ID` (`S_ID`),
  CONSTRAINT `Playlist_Songs_ibfk_1` FOREIGN KEY (`P_ID`) REFERENCES `Playlists` (`P_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `Playlist_Songs_ibfk_2` FOREIGN KEY (`S_ID`) REFERENCES `Songs` (`S_ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Playlist_Songs`
--

LOCK TABLES `Playlist_Songs` WRITE;
/*!40000 ALTER TABLE `Playlist_Songs` DISABLE KEYS */;
/*!40000 ALTER TABLE `Playlist_Songs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Playlists`
--

DROP TABLE IF EXISTS `Playlists`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Playlists` (
  `P_ID` varchar(50) NOT NULL,
  `P_Name` varchar(50) DEFAULT NULL,
  `U_ID` int NOT NULL,
  PRIMARY KEY (`P_ID`),
  KEY `fk_playlist_user` (`U_ID`),
  CONSTRAINT `fk_playlist_user` FOREIGN KEY (`U_ID`) REFERENCES `Users` (`U_ID`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Playlists`
--

LOCK TABLES `Playlists` WRITE;
/*!40000 ALTER TABLE `Playlists` DISABLE KEYS */;
/*!40000 ALTER TABLE `Playlists` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Songs`
--

DROP TABLE IF EXISTS `Songs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Songs` (
  `S_ID` varchar(50) NOT NULL,
  `S_Title` varchar(500) NOT NULL,
  `S_Artists` varchar(1000) DEFAULT NULL,
  `S_Album` varchar(500) DEFAULT NULL,
  `S_Length` BIGINT NOT NULL,
  `S_Listens` INT DEFAULT 0,
  `S_Listen_Time` BIGINT DEFAULT 0,
  `image_url` VARCHAR(500) DEFAULT NULL,
  `S_Blacklisted_Listens` INT DEFAULT 0,
  `S_Blacklisted_Time` BIGINT DEFAULT 0,
  PRIMARY KEY (`S_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Songs`
--

LOCK TABLES `Songs` WRITE;
/*!40000 ALTER TABLE `Songs` DISABLE KEYS */;
/*!40000 ALTER TABLE `Songs` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `Users`
--

DROP TABLE IF EXISTS `Users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `Users` (
  `U_ID` int NOT NULL AUTO_INCREMENT,
  `U_Username` varchar(20) NOT NULL,
  PRIMARY KEY (`U_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `Users`
--

LOCK TABLES `Users` WRITE;
/*!40000 ALTER TABLE `Users` DISABLE KEYS */;
/*!40000 ALTER TABLE `Users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-12-07 14:58:35
