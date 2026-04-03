#!/usr/bin/env python3
"""
Script to seed sample UK sponsorship jobs into the database
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import random

# Add backend to path
ROOT_DIR = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(ROOT_DIR))

load_dotenv(ROOT_DIR / '.env')

# Sample jobs data
SAMPLE_JOBS = [
    {
        "title": "Senior Software Engineer",
        "company": "TechCorp UK",
        "location": "London",
        "salary": "£60,000 - £80,000",
        "industry": "Technology",
        "description": "We are seeking an experienced Senior Software Engineer to join our growing team in London. You will work on cutting-edge cloud-based applications and lead technical initiatives.",
        "requirements": [
            "5+ years of software development experience",
            "Proficiency in Python, Java, or Go",
            "Experience with cloud platforms (AWS, Azure, or GCP)",
            "Strong understanding of microservices architecture",
            "Excellent communication skills"
        ],
        "benefits": [
            "Visa sponsorship provided",
            "Competitive salary and bonus",
            "Health insurance",
            "Pension scheme",
            "Flexible working hours"
        ],
        "sponsorship_info": "We are a licensed UK visa sponsor and will support your Skilled Worker visa application.",
        "job_type": "Full-time",
        "experience_level": "Senior"
    },
    {
        "title": "Registered Nurse",
        "company": "NHS London Trust",
        "location": "London",
        "salary": "£35,000 - £45,000",
        "industry": "Healthcare",
        "description": "Join our dedicated healthcare team as a Registered Nurse. Provide high-quality patient care in a supportive environment.",
        "requirements": [
            "Valid NMC registration",
            "Minimum 2 years nursing experience",
            "Strong clinical assessment skills",
            "Excellent patient care abilities",
            "Team player with good communication"
        ],
        "benefits": [
            "Tier 2 visa sponsorship available",
            "NHS pension scheme",
            "27 days annual leave + bank holidays",
            "Professional development opportunities",
            "Relocation assistance"
        ],
        "sponsorship_info": "NHS Trust is an approved sponsor. We assist with Health & Care Worker visa applications.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Financial Analyst",
        "company": "Global Finance Solutions",
        "location": "Manchester",
        "salary": "£45,000 - £55,000",
        "industry": "Finance",
        "description": "Analyze financial data, prepare reports, and provide insights to support business decisions.",
        "requirements": [
            "Bachelor's degree in Finance or Accounting",
            "3+ years of financial analysis experience",
            "Advanced Excel and financial modeling skills",
            "Strong analytical and problem-solving abilities",
            "Professional qualification (ACA, ACCA, or CFA) preferred"
        ],
        "benefits": [
            "Visa sponsorship for qualified candidates",
            "Performance bonuses",
            "Private healthcare",
            "Study support for professional qualifications",
            "Career progression opportunities"
        ],
        "sponsorship_info": "We sponsor Skilled Worker visas for candidates meeting the salary and skill requirements.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Civil Engineer",
        "company": "UK Infrastructure Ltd",
        "location": "Birmingham",
        "salary": "£40,000 - £60,000",
        "industry": "Engineering",
        "description": "Design and oversee construction projects including roads, bridges, and buildings.",
        "requirements": [
            "BEng/MEng in Civil Engineering",
            "Chartered Engineer status or working towards it",
            "4+ years of design and project experience",
            "Proficiency in AutoCAD and Civil 3D",
            "Knowledge of UK building regulations"
        ],
        "benefits": [
            "Skilled Worker visa sponsorship",
            "Competitive salary package",
            "Company car or allowance",
            "Professional membership fees paid",
            "Training and development programs"
        ],
        "sponsorship_info": "Licensed sponsor for engineers. We support visa applications and relocation.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Hotel Manager",
        "company": "Premium Hotels Group",
        "location": "Edinburgh",
        "salary": "£35,000 - £45,000",
        "industry": "Hospitality",
        "description": "Manage daily operations of our 4-star hotel, ensuring excellent guest experiences and team performance.",
        "requirements": [
            "Minimum 5 years hospitality management experience",
            "Proven track record in hotel operations",
            "Strong leadership and team management skills",
            "Excellent customer service orientation",
            "Budget and financial management experience"
        ],
        "benefits": [
            "Visa sponsorship available",
            "Accommodation provided",
            "Performance-based bonuses",
            "Career development opportunities",
            "Staff discounts across hotel group"
        ],
        "sponsorship_info": "We are approved to sponsor hospitality managers under the Skilled Worker route.",
        "job_type": "Full-time",
        "experience_level": "Senior"
    },
    {
        "title": "Data Scientist",
        "company": "AI Innovations Ltd",
        "location": "London",
        "salary": "£55,000 - £75,000",
        "industry": "Technology",
        "description": "Apply machine learning and statistical analysis to solve complex business problems.",
        "requirements": [
            "MSc or PhD in Data Science, Statistics, or related field",
            "3+ years of data science experience",
            "Expertise in Python, R, and SQL",
            "Experience with ML frameworks (TensorFlow, PyTorch)",
            "Strong communication skills for stakeholder engagement"
        ],
        "benefits": [
            "Tier 2 sponsorship provided",
            "Competitive salary and equity options",
            "Remote work flexibility",
            "Learning and conference budget",
            "Modern tech stack"
        ],
        "sponsorship_info": "Approved sponsor for tech professionals. Full visa application support provided.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Pharmacist",
        "company": "HealthPlus Pharmacy",
        "location": "Bristol",
        "salary": "£40,000 - £50,000",
        "industry": "Healthcare",
        "description": "Provide pharmaceutical care, dispense medications, and offer health advice to patients.",
        "requirements": [
            "GPhC registration required",
            "Degree in Pharmacy",
            "2+ years post-registration experience",
            "Strong knowledge of medicines and regulations",
            "Excellent patient counseling skills"
        ],
        "benefits": [
            "Visa sponsorship for qualified pharmacists",
            "Competitive salary",
            "GPhC fees paid",
            "Continuing professional development",
            "Work-life balance"
        ],
        "sponsorship_info": "Licensed sponsor for healthcare professionals. Health & Care Worker visa supported.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Financial Controller",
        "company": "Enterprise Finance Group",
        "location": "Leeds",
        "salary": "£65,000 - £85,000",
        "industry": "Finance",
        "description": "Oversee financial operations, reporting, and compliance for our growing organization.",
        "requirements": [
            "Qualified accountant (ACA, ACCA, CIMA)",
            "7+ years of finance experience with 3+ in management",
            "Strong knowledge of UK GAAP and IFRS",
            "Experience with ERP systems",
            "Strategic thinking and leadership skills"
        ],
        "benefits": [
            "Visa sponsorship for senior roles",
            "Executive compensation package",
            "Private healthcare for family",
            "Performance bonuses",
            "Career progression to CFO"
        ],
        "sponsorship_info": "We sponsor senior financial professionals under Skilled Worker visa route.",
        "job_type": "Full-time",
        "experience_level": "Senior"
    },
    {
        "title": "Mechanical Engineer",
        "company": "Advanced Manufacturing UK",
        "location": "Sheffield",
        "salary": "£38,000 - £52,000",
        "industry": "Engineering",
        "description": "Design and develop mechanical systems for manufacturing and industrial applications.",
        "requirements": [
            "BEng/MEng in Mechanical Engineering",
            "3+ years of design and development experience",
            "Proficiency in SolidWorks or similar CAD software",
            "Knowledge of manufacturing processes",
            "Problem-solving and analytical skills"
        ],
        "benefits": [
            "Skilled Worker visa sponsorship",
            "Relocation package",
            "Training and professional development",
            "Company pension",
            "Life insurance"
        ],
        "sponsorship_info": "Approved sponsor for engineers. We assist with visa applications and settlement.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Restaurant Manager",
        "company": "Gourmet Dining Group",
        "location": "Manchester",
        "salary": "£32,000 - £40,000",
        "industry": "Hospitality",
        "description": "Lead restaurant operations, manage staff, and ensure exceptional dining experiences.",
        "requirements": [
            "4+ years restaurant management experience",
            "Strong leadership and team development skills",
            "Knowledge of food safety and hygiene regulations",
            "Budget management and cost control experience",
            "Passion for hospitality and customer service"
        ],
        "benefits": [
            "Visa sponsorship available",
            "Performance bonuses",
            "Staff meals",
            "Career advancement opportunities",
            "Dynamic work environment"
        ],
        "sponsorship_info": "Licensed to sponsor restaurant and catering managers under Skilled Worker visa.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "DevOps Engineer",
        "company": "CloudTech Solutions",
        "location": "Cambridge",
        "salary": "£50,000 - £70,000",
        "industry": "Technology",
        "description": "Build and maintain CI/CD pipelines, automate infrastructure, and ensure system reliability.",
        "requirements": [
            "4+ years of DevOps or SRE experience",
            "Strong knowledge of AWS/Azure/GCP",
            "Experience with Docker, Kubernetes, Terraform",
            "Proficiency in scripting (Python, Bash)",
            "Understanding of security best practices"
        ],
        "benefits": [
            "Tier 2 visa sponsorship",
            "Flexible remote work",
            "Latest tools and technologies",
            "Learning budget",
            "Stock options"
        ],
        "sponsorship_info": "Approved UK visa sponsor for tech professionals. Full support for visa process.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Pediatric Nurse",
        "company": "Children's Hospital Trust",
        "location": "Glasgow",
        "salary": "£33,000 - £43,000",
        "industry": "Healthcare",
        "description": "Provide specialized nursing care for children and young people in hospital settings.",
        "requirements": [
            "NMC registration with pediatric qualification",
            "Minimum 2 years pediatric nursing experience",
            "Excellent communication with children and families",
            "Strong clinical skills",
            "Compassionate and patient-centered approach"
        ],
        "benefits": [
            "Health & Care Worker visa sponsorship",
            "NHS pension and benefits",
            "Generous annual leave",
            "Specialist training opportunities",
            "Supportive team environment"
        ],
        "sponsorship_info": "NHS approved sponsor. We support international nurses with visa applications.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    },
    {
        "title": "Investment Analyst",
        "company": "Capital Investments Ltd",
        "location": "London",
        "salary": "£48,000 - £62,000",
        "industry": "Finance",
        "description": "Analyze investment opportunities, conduct research, and support portfolio management.",
        "requirements": [
            "Degree in Finance, Economics, or related field",
            "2+ years investment analysis experience",
            "Strong financial modeling and valuation skills",
            "CFA Level 1 or working towards it",
            "Excellent research and analytical abilities"
        ],
        "benefits": [
            "Visa sponsorship for qualified analysts",
            "Competitive bonus structure",
            "CFA study support",
            "Private healthcare",
            "Career development programs"
        ],
        "sponsorship_info": "Licensed sponsor for financial services professionals. Skilled Worker visa supported.",
        "job_type": "Full-time",
        "experience_level": "Entry"
    },
    {
        "title": "Electrical Engineer",
        "company": "Power Systems Engineering",
        "location": "Newcastle",
        "salary": "£42,000 - £58,000",
        "industry": "Engineering",
        "description": "Design electrical systems, oversee installations, and ensure compliance with regulations.",
        "requirements": [
            "BEng/MEng in Electrical Engineering",
            "Chartered or working towards IET membership",
            "5+ years of electrical design experience",
            "Knowledge of BS 7671 wiring regulations",
            "Project management skills"
        ],
        "benefits": [
            "Skilled Worker visa sponsorship",
            "Competitive salary package",
            "Professional development support",
            "Company vehicle",
            "Pension and life insurance"
        ],
        "sponsorship_info": "Approved sponsor for electrical engineers. Full visa application assistance provided.",
        "job_type": "Full-time",
        "experience_level": "Senior"
    },
    {
        "title": "Head Chef",
        "company": "Fine Dining Restaurants",
        "location": "Bath",
        "salary": "£38,000 - £48,000",
        "industry": "Hospitality",
        "description": "Lead kitchen operations, create menus, and maintain high culinary standards.",
        "requirements": [
            "Culinary degree or equivalent experience",
            "5+ years as Head Chef or Sous Chef",
            "Creative menu development skills",
            "Strong team leadership and training abilities",
            "Knowledge of food costs and kitchen management"
        ],
        "benefits": [
            "Visa sponsorship available",
            "Competitive salary",
            "Creative freedom in menu design",
            "Staff accommodation options",
            "Career growth opportunities"
        ],
        "sponsorship_info": "Licensed to sponsor head chefs under Skilled Worker visa route.",
        "job_type": "Full-time",
        "experience_level": "Senior"
    },
    {
        "title": "Frontend Developer",
        "company": "Digital Innovations",
        "location": "Brighton",
        "salary": "£40,000 - £55,000",
        "industry": "Technology",
        "description": "Build modern, responsive web applications using React and other frontend technologies.",
        "requirements": [
            "3+ years of frontend development experience",
            "Expert knowledge of React, JavaScript, HTML, CSS",
            "Experience with TypeScript and modern build tools",
            "Understanding of UX/UI principles",
            "Portfolio of production applications"
        ],
        "benefits": [
            "Tier 2 visa sponsorship",
            "Remote-first culture",
            "Modern tech stack",
            "Learning and development budget",
            "Flexible working hours"
        ],
        "sponsorship_info": "Approved sponsor for software developers. We support visa applications.",
        "job_type": "Full-time",
        "experience_level": "Mid"
    }
]

async def seed_jobs():
    """Seed sample jobs into the database"""
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Clear existing jobs
    await db.jobs.delete_many({})
    print("Cleared existing jobs")
    
    # Insert sample jobs
    jobs_to_insert = []
    for job_data in SAMPLE_JOBS:
        job_data['id'] = str(random.randint(100000, 999999))
        # Randomize posted date within last 30 days
        days_ago = random.randint(0, 30)
        job_data['posted_date'] = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
        jobs_to_insert.append(job_data)
    
    await db.jobs.insert_many(jobs_to_insert)
    print(f"Successfully seeded {len(jobs_to_insert)} jobs into the database")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_jobs())
