-- ============================================================
--  Northwind Database -- Analytical Queries & Stored Procedure
--  Compatible with: MS SQL Server 2016+ (T-SQL)
--  Data Source: Microsoft Northwind sample database
--  https://github.com/microsoft/sql-server-samples
-- ============================================================


-- ============================================================
-- QUERY 1: Total Revenue by Product Category
--           Sorted highest revenue first
-- ============================================================

SELECT
    c.CategoryName,

    -- SUM of (unit price at time of order * quantity) less any discount applied
    -- We use od.UnitPrice (not p.UnitPrice) because prices may have changed after the order
    SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS TotalRevenue,

    -- Count of distinct products sold in this category (useful context)
    COUNT(DISTINCT od.ProductID)                         AS ProductsSold,

    -- Count of total line items (order rows) for this category
    COUNT(*)                                             AS TotalLineItems

FROM Categories          AS c
JOIN Products            AS p  ON p.CategoryID  = c.CategoryID
JOIN [Order Details]     AS od ON od.ProductID  = p.ProductID

GROUP BY c.CategoryName

-- Highest revenue category at the top
ORDER BY TotalRevenue DESC;


-- ============================================================
-- QUERY 2: Top 10 Customers by Lifetime Order Value
--           Including their most recent order date
-- ============================================================

SELECT TOP 10
    cu.CustomerID,
    cu.CompanyName,
    cu.Country,

    -- Lifetime value: all orders, all line items, net of discounts
    SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS LifetimeOrderValue,

    -- Total number of distinct orders the customer placed
    COUNT(DISTINCT o.OrderID)                            AS TotalOrders,

    -- Most recent order placed by this customer
    MAX(o.OrderDate)                                     AS MostRecentOrderDate

FROM Customers           AS cu
JOIN Orders              AS o  ON o.CustomerID  = cu.CustomerID
JOIN [Order Details]     AS od ON od.OrderID    = o.OrderID

GROUP BY cu.CustomerID, cu.CompanyName, cu.Country

-- Rank by lifetime value descending, keep only the top 10
ORDER BY LifetimeOrderValue DESC;


-- ============================================================
-- QUERY 3: Delayed Orders
--           Shipped more than 7 calendar days after order date
-- ============================================================

SELECT
    o.OrderID,
    o.CustomerID,
    cu.CompanyName,
    o.EmployeeID,
    o.OrderDate,
    o.ShippedDate,

    -- How many days elapsed between order placement and shipment
    DATEDIFF(DAY, o.OrderDate, o.ShippedDate)           AS DaysToShip,

    -- Explicit delay flag for easy filtering / reporting
    'DELAYED'                                            AS ShipmentStatus,

    -- Optional: the required (promised) date for context
    o.RequiredDate,

    -- Flag whether it was also past the required date
    CASE
        WHEN o.ShippedDate > o.RequiredDate THEN 'YES'
        ELSE 'NO'
    END                                                  AS PastRequiredDate

FROM Orders              AS o
JOIN Customers           AS cu ON cu.CustomerID = o.CustomerID

WHERE
    -- Only consider orders that have actually shipped (exclude NULLs)
    o.ShippedDate IS NOT NULL

    -- Core delay condition: more than 7 days from order to ship
    AND DATEDIFF(DAY, o.OrderDate, o.ShippedDate) > 7

ORDER BY DaysToShip DESC;   -- Worst delays at the top


-- ============================================================
-- STORED PROCEDURE: usp_NorthwindSalesReport
--
-- Purpose : Encapsulates all three analytical queries above
--           into a single callable procedure. Supports optional
--           date-range filtering and a configurable delay threshold.
--
-- Parameters:
--   @StartDate       DATE    -- Filter orders on/after this date  (NULL = no lower bound)
--   @EndDate         DATE    -- Filter orders on/before this date (NULL = no upper bound)
--   @DelayThreshold  INT     -- Days-to-ship > this value = delayed (default 7)
--   @TopN            INT     -- How many top customers to return   (default 10)
--
-- Usage examples:
--   EXEC usp_NorthwindSalesReport;                         -- defaults, all dates
--   EXEC usp_NorthwindSalesReport @StartDate = '1997-01-01', @EndDate = '1997-12-31';
--   EXEC usp_NorthwindSalesReport @DelayThreshold = 14, @TopN = 5;
-- ============================================================

-- Drop the procedure if it already exists so we can recreate cleanly
IF OBJECT_ID('dbo.usp_NorthwindSalesReport', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_NorthwindSalesReport;
GO

CREATE PROCEDURE dbo.usp_NorthwindSalesReport
    @StartDate      DATE = NULL,   -- Optional lower bound on OrderDate
    @EndDate        DATE = NULL,   -- Optional upper bound on OrderDate
    @DelayThreshold INT  = 7,      -- Days-to-ship threshold for "delayed" flag
    @TopN           INT  = 10      -- Number of top customers to return
AS
BEGIN
    -- Suppress row-count messages (cleaner for application consumption)
    SET NOCOUNT ON;

    -- ----------------------------------------------------------
    -- SECTION 1: Revenue by Category (filtered by date range)
    -- ----------------------------------------------------------
    SELECT
        c.CategoryName,
        SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS TotalRevenue,
        COUNT(DISTINCT od.ProductID)                         AS ProductsSold,
        COUNT(*)                                             AS TotalLineItems
    FROM Categories      AS c
    JOIN Products        AS p  ON p.CategoryID = c.CategoryID
    JOIN [Order Details] AS od ON od.ProductID = p.ProductID
    JOIN Orders          AS o  ON o.OrderID    = od.OrderID
    WHERE
        -- Apply date filter only when the caller supplies a value
        (@StartDate IS NULL OR o.OrderDate >= @StartDate)
        AND (@EndDate IS NULL OR o.OrderDate <= @EndDate)
    GROUP BY c.CategoryName
    ORDER BY TotalRevenue DESC;

    -- ----------------------------------------------------------
    -- SECTION 2: Top-N Customers by Lifetime Value
    -- ----------------------------------------------------------
    SELECT TOP (@TopN)
        cu.CustomerID,
        cu.CompanyName,
        cu.Country,
        SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS LifetimeOrderValue,
        COUNT(DISTINCT o.OrderID)                            AS TotalOrders,
        MAX(o.OrderDate)                                     AS MostRecentOrderDate
    FROM Customers       AS cu
    JOIN Orders          AS o  ON o.CustomerID = cu.CustomerID
    JOIN [Order Details] AS od ON od.OrderID   = o.OrderID
    WHERE
        (@StartDate IS NULL OR o.OrderDate >= @StartDate)
        AND (@EndDate IS NULL OR o.OrderDate <= @EndDate)
    GROUP BY cu.CustomerID, cu.CompanyName, cu.Country
    ORDER BY LifetimeOrderValue DESC;

    -- ----------------------------------------------------------
    -- SECTION 3: Delayed Orders (using the configurable threshold)
    -- ----------------------------------------------------------
    SELECT
        o.OrderID,
        o.CustomerID,
        cu.CompanyName,
        o.OrderDate,
        o.ShippedDate,
        DATEDIFF(DAY, o.OrderDate, o.ShippedDate)           AS DaysToShip,
        'DELAYED'                                            AS ShipmentStatus,
        o.RequiredDate,
        CASE
            WHEN o.ShippedDate > o.RequiredDate THEN 'YES'
            ELSE 'NO'
        END                                                  AS PastRequiredDate
    FROM Orders          AS o
    JOIN Customers       AS cu ON cu.CustomerID = o.CustomerID
    WHERE
        o.ShippedDate IS NOT NULL
        AND DATEDIFF(DAY, o.OrderDate, o.ShippedDate) > @DelayThreshold
        AND (@StartDate IS NULL OR o.OrderDate >= @StartDate)
        AND (@EndDate IS NULL OR o.OrderDate <= @EndDate)
    ORDER BY DaysToShip DESC;

END;
GO

-- ============================================================
-- Quick sanity-check: run the procedure with defaults
-- Uncomment the line below to test after restoring Northwind:
-- EXEC dbo.usp_NorthwindSalesReport;
-- ============================================================
