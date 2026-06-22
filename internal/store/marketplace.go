package store

import (
	"database/sql"
	"time"

	"github.com/agent-platform/internal/model"
)

// ── Migration ──

func (s *Store) migrateMarketplace() error {
	_, err := s.DB.Exec(`
		CREATE TABLE IF NOT EXISTS marketplace_agents (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			user_id INTEGER NOT NULL,
			title TEXT NOT NULL,
			function TEXT DEFAULT '',
			description TEXT DEFAULT '',
			icon TEXT DEFAULT '',
			access_url TEXT DEFAULT '',
			knowledge_url TEXT DEFAULT '',
			tags TEXT DEFAULT '[]',
			author TEXT DEFAULT '',
			usage_count INTEGER DEFAULT 0,
			category TEXT DEFAULT '',
			featured INTEGER DEFAULT 0,
			created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (user_id) REFERENCES users(id)
		)
	`)
	if err != nil {
		return err
	}

	// Add columns if they don't exist (for existing databases)
	s.DB.Exec(`ALTER TABLE marketplace_agents ADD COLUMN function TEXT DEFAULT ''`)
	s.DB.Exec(`ALTER TABLE marketplace_agents ADD COLUMN access_url TEXT DEFAULT ''`)
	s.DB.Exec(`ALTER TABLE marketplace_agents ADD COLUMN knowledge_url TEXT DEFAULT ''`)

	return nil
}

// ── CRUD ──

func (s *Store) CreateMarketAgent(userID int64, req *model.MarketAgentCreate) (*model.MarketAgent, error) {
	now := time.Now()
	result, err := s.DB.Exec(
		`INSERT INTO marketplace_agents (user_id, title, function, description, icon, access_url, knowledge_url, tags, author, category, featured, created_at, updated_at)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		userID, req.Title, req.Function, req.Description, req.Icon, req.AccessURL, req.KnowledgeURL, req.Tags, req.Author, req.Category, boolToInt(req.Featured), now, now,
	)
	if err != nil {
		return nil, err
	}
	id, _ := result.LastInsertId()
	return s.GetMarketAgent(id)
}

func (s *Store) GetMarketAgent(id int64) (*model.MarketAgent, error) {
	a := &model.MarketAgent{}
	var createdAt, updatedAt string
	err := s.DB.QueryRow(
		`SELECT id, user_id, title, function, description, icon, access_url, knowledge_url, tags, author, usage_count, category, featured, created_at, updated_at
		 FROM marketplace_agents WHERE id = ?`, id,
	).Scan(&a.ID, &a.UserID, &a.Title, &a.Function, &a.Description, &a.Icon, &a.AccessURL, &a.KnowledgeURL, &a.Tags,
		&a.Author, &a.UsageCount, &a.Category, &a.Featured, &createdAt, &updatedAt)
	if err != nil {
		return nil, err
	}
	a.CreatedAt, _ = parseTime(createdAt)
	a.UpdatedAt, _ = parseTime(updatedAt)
	return a, nil
}

func (s *Store) ListMarketAgents(category string, page, pageSize int) ([]*model.MarketAgent, int, error) {
	if pageSize <= 0 {
		pageSize = 50
	}
	if page <= 0 {
		page = 1
	}

	var rows *sql.Rows
	var err error
	var total int

	if category != "" && category != "全部" {
		err = s.DB.QueryRow(`SELECT COUNT(*) FROM marketplace_agents WHERE category = ?`, category).Scan(&total)
		if err != nil {
			return nil, 0, err
		}
		rows, err = s.DB.Query(
			`SELECT id, user_id, title, function, description, icon, access_url, knowledge_url, tags, author, usage_count, category, featured, created_at, updated_at
			 FROM marketplace_agents WHERE category = ? ORDER BY featured DESC, updated_at DESC LIMIT ? OFFSET ?`,
			category, pageSize, (page-1)*pageSize,
		)
	} else {
		err = s.DB.QueryRow(`SELECT COUNT(*) FROM marketplace_agents`).Scan(&total)
		if err != nil {
			return nil, 0, err
		}
		rows, err = s.DB.Query(
			`SELECT id, user_id, title, function, description, icon, access_url, knowledge_url, tags, author, usage_count, category, featured, created_at, updated_at
			 FROM marketplace_agents ORDER BY featured DESC, updated_at DESC LIMIT ? OFFSET ?`,
			pageSize, (page-1)*pageSize,
		)
	}
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	var agents []*model.MarketAgent
	for rows.Next() {
		a := &model.MarketAgent{}
		var ca, ua string
		if err := rows.Scan(&a.ID, &a.UserID, &a.Title, &a.Function, &a.Description, &a.Icon, &a.AccessURL, &a.KnowledgeURL, &a.Tags,
			&a.Author, &a.UsageCount, &a.Category, &a.Featured, &ca, &ua); err != nil {
			return nil, 0, err
		}
		a.CreatedAt, _ = parseTime(ca)
		a.UpdatedAt, _ = parseTime(ua)
		agents = append(agents, a)
	}
	return agents, total, nil
}

func (s *Store) UpdateMarketAgent(id int64, req *model.MarketAgentUpdate) (*model.MarketAgent, error) {
	now := time.Now()
	if req.Title != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET title=?, updated_at=? WHERE id=?`, *req.Title, now, id)
	}
	if req.Function != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET function=?, updated_at=? WHERE id=?`, *req.Function, now, id)
	}
	if req.Description != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET description=?, updated_at=? WHERE id=?`, *req.Description, now, id)
	}
	if req.AccessURL != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET access_url=?, updated_at=? WHERE id=?`, *req.AccessURL, now, id)
	}
	if req.KnowledgeURL != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET knowledge_url=?, updated_at=? WHERE id=?`, *req.KnowledgeURL, now, id)
	}
	if req.Tags != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET tags=?, updated_at=? WHERE id=?`, *req.Tags, now, id)
	}
	if req.Author != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET author=?, updated_at=? WHERE id=?`, *req.Author, now, id)
	}
	if req.Category != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET category=?, updated_at=? WHERE id=?`, *req.Category, now, id)
	}
	if req.Featured != nil {
		_, _ = s.DB.Exec(`UPDATE marketplace_agents SET featured=?, updated_at=? WHERE id=?`, boolToInt(*req.Featured), now, id)
	}
	return s.GetMarketAgent(id)
}

func (s *Store) DeleteMarketAgent(id int64) error {
	_, err := s.DB.Exec(`DELETE FROM marketplace_agents WHERE id = ?`, id)
	return err
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}
