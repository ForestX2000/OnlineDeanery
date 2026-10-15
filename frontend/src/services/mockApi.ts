export interface LoginResponse {
  success: boolean;
  token: string;
  user: {
    email: string;
    firstName: string;
    lastName: string;
    role: "student" | "admin";
  };
}

export interface AnalyzeResponse {
  success: boolean;
  data: {
    extracted_fields: Record<string, string>;
    answer: string;
    sources: { type: string; reference: string }[];
  };
}


interface MockUser {
  email: string;
  password: string;
  firstName: string;
  lastName: string;
  role: "student" | "admin";
}

const MOCK_USERS: MockUser[] = [
  {
    email: "student@university.ru",
    password: "123456",
    firstName: "Иван",
    lastName: "Студентов",
    role: "student",
  },
  {
    email: "admin@university.ru",
    password: "admin123",
    firstName: "Алексей",
    lastName: "Админов",
    role: "admin",
  },
  {
    email: "test@university.ru",
    password: "test123",
    firstName: "Мария",
    lastName: "Петрова",
    role: "student",
  },
];


const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const mockApi = {
  async login(email: string, password: string): Promise<LoginResponse> {
    await delay(1000);

    const normalizedEmail = email.toLowerCase().trim();
    const user = MOCK_USERS.find((u) => u.email.toLowerCase() === normalizedEmail);

    if (!user) {
      throw new Error("Пользователь с таким email не найден. Проверьте адрес или зарегистрируйтесь.");
    }

    if (user.password !== password) {
      throw new Error("Неверный пароль.");
    }

    return {
      success: true,
      token: `fake-jwt-token-${Date.now()}`,
      user: {
        email: user.email,
        firstName: user.firstName,
        lastName: user.lastName,
        role: user.role,
      },
    };
  },

  async register(data: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
  }): Promise<LoginResponse> {
    await delay(1200);

    const normalizedEmail = data.email.toLowerCase().trim();
    const existingUser = MOCK_USERS.find((u) => u.email.toLowerCase() === normalizedEmail);

    if (existingUser) {
      throw new Error("Пользователь с таким email уже зарегистрирован. Попробуйте войти.");
    }


    
    return {
      success: true,
      token: `fake-jwt-token-${Date.now()}`,
      user: {
        email: data.email,
        firstName: data.firstName,
        lastName: data.lastName,
        role: "student", 
      },
    };
  },

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  async analyzeDocument(_file: File, docType: string, _question: string): Promise<AnalyzeResponse> {
    await delay(2500); 

    if (docType === "study_certificate") {
      return {
        success: true,
        data: {
          extracted_fields: {
            фио: "Студентов Иван Петрович",
            номер_зачетной_книжки: "2023-ИТ-045",
            факультет: "Факультет компьютерных наук",
            курс: "3",
            форма_обучения: "Очная",
            статус: "Действительно обучается",
          },
          answer: "Согласно предоставленной справке, вы действительно являетесь студентом 3 курса Факультета компьютерных наук. Документ действителен и подписан деканом.",
          sources: [
            { type: "документ", reference: "Справка об обучении №451/23, стр. 1" },
            { type: "положение", reference: "Положение о порядке выдачи справок, п. 2.1" },
          ],
        },
      };
    }

    return {
      success: true,
      data: {
        extracted_fields: {
          тип_документа: docType,
          дата_выдачи: "10.10.2026",
          ответственный: "Петрова А.С.",
        },
        answer: "Документ успешно обработан. Основная информация извлечена.",
        sources: [{ type: "документ", reference: "Загруженный файл" }],
      },
    };
  },
};
